<?php
declare(strict_types=1);

namespace DownAccessReport;

use PHPMailer\PHPMailer\Exception as PHPMailerException;
use PHPMailer\PHPMailer\PHPMailer;
use Throwable;

final class DownAccessReportHandler
{
    private const SMTP_HOST     = 'smtp.mail.ovh.net';
    private const SMTP_PORT     = 465;
    private const SMTP_USERNAME = 'app-notification@mathieumartin.ovh';
    private const SMTP_FROM     = 'app-notification@mathieumartin.ovh';
    private const REPORT_TO     = 'contact@mathieumartin.ovh';

    private const SMTP_PASSWORD_ENV = 'APPCLAVIER_SMTP_PASS';
    private const BEARER_SECRET_ENV = 'DOWNACCESS_BEARER_SECRET';

    private const MAX_VERBOSE_LOG_BYTES = 100_000;
    private const MAX_COMMENT_BYTES     = 2_000;

    public function __construct(
        private readonly RateLimiter $rateLimiter,
    ) {
    }

    public function handle(string $requestMethod, string $rawBody, array $server, array $post = [], array $files = []): array
    {
        if (strtoupper($requestMethod) !== 'POST') {
            return [405, $this->error('method_not_allowed', 'Méthode non autorisée.')];
        }

        // Vérification du Bearer token
        $authHeader = trim((string) ($server['HTTP_AUTHORIZATION'] ?? ''));
        $expectedSecret = getenv(self::BEARER_SECRET_ENV) ?: '';
        if ($expectedSecret === '' || $authHeader !== 'Bearer ' . $expectedSecret) {
            return [401, $this->error('unauthorized', 'Accès non autorisé.')];
        }

        // Support multipart (champ "report" JSON + fichier "log_file") ou JSON brut
        if (isset($post['report'])) {
            $payload = json_decode($post['report'], true);
        } else {
            $payload = json_decode($rawBody, true);
        }

        if (!is_array($payload)) {
            return [400, $this->error('invalid_json', 'JSON invalide.')];
        }

        // Récupérer le fichier log si envoyé en pièce jointe
        $logFilePath = null;
        $logFileName = null;
        if (isset($files['log_file']) && $files['log_file']['error'] === UPLOAD_ERR_OK) {
            $logFilePath = $files['log_file']['tmp_name'];
            $logFileName = $files['log_file']['name'] ?: 'downaccess.log';
        }

        $validationError = $this->validate($payload);
        if ($validationError !== null) {
            return [422, $this->error('validation_error', $validationError)];
        }

        $clientIp = $this->resolveClientIp($server);
        try {
            if (!$this->rateLimiter->allow($clientIp)) {
                return [429, $this->error('rate_limited', 'Trop de rapports envoyés récemment.')];
            }
        } catch (Throwable) {
            return [500, $this->error('server_error', "Le rapport n'a pas pu être envoyé.")];
        }

        try {
            $this->sendMail($payload, $logFilePath, $logFileName);
        } catch (Throwable $e) {
            return [500, $this->error('server_error', "Envoi email échoué : " . $e->getMessage())];
        }

        return [200, ['ok' => true, 'message' => 'Rapport envoyé avec succès.']];
    }

    private function validate(array $p): ?string
    {
        if (trim((string) ($p['error_message'] ?? '')) === '') {
            return 'Le message d\'erreur est obligatoire.';
        }
        if (trim((string) ($p['app_version'] ?? '')) === '') {
            return 'La version de l\'application est obligatoire.';
        }
        return null;
    }

    private function sendMail(array $p, ?string $logFilePath = null, ?string $logFileName = null): void
    {
        $smtpPass = trim(getenv(self::SMTP_PASSWORD_ENV) ?: '', '" ');
        if ($smtpPass === '') {
            throw new PHPMailerException('SMTP password missing.');
        }

        $appVersion   = $this->str($p, 'app_version');
        $ytdlpVersion = $this->str($p, 'ytdlp_version');
        $os           = $this->str($p, 'os');
        $timestamp    = $this->str($p, 'timestamp');
        $url          = $this->str($p, 'url');
        $site         = $this->str($p, 'site');
        $formatSpec   = $this->str($p, 'format_spec');
        $errorMessage = $this->str($p, 'error_message');
        $verboseLog   = substr($this->str($p, 'verbose_log'), 0, self::MAX_VERBOSE_LOG_BYTES);
        $userComment  = substr($this->str($p, 'user_comment'), 0, self::MAX_COMMENT_BYTES);
        $email        = substr($this->str($p, 'email'), 0, 200);
        $systemInfo   = is_array($p['system_info'] ?? null) ? $p['system_info'] : [];
        $preferences  = is_array($p['preferences'] ?? null) ? $p['preferences'] : [];
        $queueState   = is_array($p['queue_state'] ?? null) ? $p['queue_state'] : [];

        $mailer = new PHPMailer(true);
        $mailer->isSMTP();
        $mailer->Host       = self::SMTP_HOST;
        $mailer->Port       = self::SMTP_PORT;
        $mailer->SMTPAuth   = true;
        $mailer->SMTPSecure = PHPMailer::ENCRYPTION_SMTPS;
        $mailer->Username   = self::SMTP_USERNAME;
        $mailer->Password   = $smtpPass;
        $mailer->CharSet    = 'UTF-8';
        $mailer->Encoding   = 'base64';

        $mailer->setFrom(self::SMTP_FROM, 'DownAccess Error Reporter');
        $mailer->addAddress(self::REPORT_TO);
        if ($email !== '' && filter_var($email, FILTER_VALIDATE_EMAIL)) {
            $mailer->addReplyTo($email);
        }

        $mailer->Subject = sprintf(
            '[DownAccess] Erreur — %s — v%s — %s',
            $site ?: 'inconnu',
            $appVersion,
            gmdate('Y-m-d H:i', strtotime($timestamp) ?: time())
        );

        $mailer->isHTML(true);
        $mailer->Body    = $this->buildHtmlBody(
            $appVersion, $ytdlpVersion, $os, $timestamp,
            $url, $site, $formatSpec, $errorMessage, $verboseLog, $userComment, $email,
            $systemInfo, $preferences, $queueState
        );
        $mailer->AltBody = $this->buildTextBody(
            $appVersion, $ytdlpVersion, $os, $timestamp,
            $url, $site, $formatSpec, $errorMessage, $verboseLog, $userComment, $email,
            $systemInfo, $preferences, $queueState
        );

        // Joindre le fichier log si disponible
        if ($logFilePath !== null && file_exists($logFilePath)) {
            $mailer->addAttachment($logFilePath, $logFileName ?? 'downaccess.log', 'base64', 'text/plain');
        }

        $mailer->send();
    }

    private function buildHtmlBody(
        string $appVersion, string $ytdlpVersion, string $os, string $timestamp,
        string $url, string $site, string $formatSpec, string $errorMessage,
        string $verboseLog, string $userComment, string $email = '',
        array $systemInfo = [], array $preferences = [], array $queueState = []
    ): string {
        $h = fn(string $s): string => htmlspecialchars($s, ENT_QUOTES | ENT_HTML5, 'UTF-8');

        $rows = [
            ['Version DownAccess', $appVersion],
            ['Version yt-dlp',     $ytdlpVersion],
            ['Système',            $os],
            ['Date',               $timestamp],
            ['URL',                $url],
            ['Site',               $site],
            ['Format',             $formatSpec],
            ['Email utilisateur',  $email ?: '—'],
        ];

        $tableRows = '';
        foreach ($rows as [$label, $value]) {
            $tableRows .= sprintf(
                '<tr><td style="padding:4px 8px;font-weight:bold;white-space:nowrap;">%s</td>'
                . '<td style="padding:4px 8px;word-break:break-all;">%s</td></tr>',
                $h($label),
                $h($value)
            );
        }

        // Sections diagnostic rendues génériquement : tout champ ajouté côté
        // app apparaît automatiquement, sans retoucher ce fichier.
        $systemBlock = $systemInfo !== []
            ? '<h3>Informations système</h3>' . $this->kvTableHtml($systemInfo, $h)
            : '';
        $prefsBlock = $preferences !== []
            ? '<h3>Préférences</h3>' . $this->kvTableHtml($preferences, $h)
            : '';
        $queueBlock = $this->queueHtml($queueState, $h);

        $commentBlock = $userComment !== ''
            ? '<h3>Commentaire utilisateur</h3><p style="background:#fffde7;padding:8px;">' . $h($userComment) . '</p>'
            : '';

        $verboseBlock = $verboseLog !== ''
            ? '<h3>Log diagnostic (yt-dlp verbose)</h3><pre style="background:#f5f5f5;padding:8px;font-size:11px;overflow:auto;">'
              . $h($verboseLog) . '</pre>'
            : '';

        return <<<HTML
        <!DOCTYPE html><html><head><meta charset="UTF-8"></head><body>
        <h2 style="color:#c00;">Rapport d'erreur DownAccess</h2>

        <h3>Informations techniques</h3>
        <table border="1" cellspacing="0" style="border-collapse:collapse;">
        {$tableRows}
        </table>

        {$systemBlock}
        {$prefsBlock}
        {$queueBlock}

        <h3>Message d'erreur</h3>
        <pre style="background:#fff0f0;padding:8px;color:#c00;">{$h($errorMessage)}</pre>

        {$commentBlock}
        {$verboseBlock}
        </body></html>
        HTML;
    }

    private function buildTextBody(
        string $appVersion, string $ytdlpVersion, string $os, string $timestamp,
        string $url, string $site, string $formatSpec, string $errorMessage,
        string $verboseLog, string $userComment, string $email = '',
        array $systemInfo = [], array $preferences = [], array $queueState = []
    ): string {
        $lines = [
            "RAPPORT D'ERREUR DOWNACCESS",
            str_repeat('=', 40),
            "Version DownAccess : $appVersion",
            "Version yt-dlp     : $ytdlpVersion",
            "Système            : $os",
            "Date               : $timestamp",
            "URL                : $url",
            "Site               : $site",
            "Format             : $formatSpec",
            "Email utilisateur  : " . ($email ?: '—'),
        ];

        if ($systemInfo !== []) {
            $lines[] = '';
            $lines[] = 'INFORMATIONS SYSTÈME :';
            foreach ($systemInfo as $key => $value) {
                $lines[] = '  ' . $this->systemLabel((string) $key) . ' : ' . $this->scalarStr($value);
            }
        }

        if ($preferences !== []) {
            $lines[] = '';
            $lines[] = 'PRÉFÉRENCES :';
            foreach ($preferences as $key => $value) {
                $lines[] = '  ' . $this->systemLabel((string) $key) . ' : ' . $this->scalarStr($value);
            }
        }

        $queueText = $this->queueText($queueState);
        if ($queueText !== '') {
            $lines[] = '';
            $lines[] = "FILE D'ATTENTE :";
            $lines[] = $queueText;
        }

        $lines[] = '';
        $lines[] = 'ERREUR :';
        $lines[] = $errorMessage;

        if ($userComment !== '') {
            $lines[] = '';
            $lines[] = 'COMMENTAIRE UTILISATEUR :';
            $lines[] = $userComment;
        }

        if ($verboseLog !== '') {
            $lines[] = '';
            $lines[] = 'LOG DIAGNOSTIC :';
            $lines[] = $verboseLog;
        }

        return implode(PHP_EOL, $lines);
    }

    private function str(array $p, string $key): string
    {
        $v = $p[$key] ?? '';
        return trim(is_string($v) ? $v : (string) $v);
    }

    /** Libellé lisible pour une clé de system_info (fallback : la clé brute). */
    private function systemLabel(string $key): string
    {
        static $labels = [
            'python'           => 'Python',
            'wxpython'         => 'wxPython',
            'ffmpeg'           => 'FFmpeg',
            'ram_available_mb' => 'RAM disponible (Mo)',
            'ram_total_mb'     => 'RAM totale (Mo)',
            'os_platform'      => 'Plateforme OS',
            'os_edition'       => 'Édition Windows',
            'architecture'     => 'Architecture',
            'cpu'              => 'Processeur',
            'cpu_count'        => 'Cœurs CPU',
            'disk_free_gb'     => 'Disque libre (Go)',
            'disk_total_gb'    => 'Disque total (Go)',
            'system_locale'    => 'Locale système',
            'app_language'     => "Langue de l'application",
            'screen_reader'    => "Lecteur d'écran",
            'frozen'           => 'Exécutable compilé',
        ];
        return $labels[$key] ?? $key;
    }

    /** Convertit une valeur scalaire (bool/int/float/string/array) en texte. */
    private function scalarStr(mixed $v): string
    {
        if (is_bool($v)) {
            return $v ? 'oui' : 'non';
        }
        if (is_array($v)) {
            return json_encode($v, JSON_UNESCAPED_UNICODE) ?: '—';
        }
        return (string) $v;
    }

    /** Table HTML clé → valeur générique (libellés via systemLabel, valeurs via scalarStr). */
    private function kvTableHtml(array $data, callable $h): string
    {
        $rows = '';
        foreach ($data as $key => $value) {
            $rows .= sprintf(
                '<tr><td style="padding:4px 8px;font-weight:bold;white-space:nowrap;">%s</td>'
                . '<td style="padding:4px 8px;word-break:break-all;">%s</td></tr>',
                $h($this->systemLabel((string) $key)),
                $h($this->scalarStr($value))
            );
        }
        return '<table border="1" cellspacing="0" style="border-collapse:collapse;">' . $rows . '</table>';
    }

    /** Section HTML « File d'attente » (en cours + en attente). Vide si rien. */
    private function queueHtml(array $queue, callable $h): string
    {
        $active  = is_array($queue['active']  ?? null) ? $queue['active']  : [];
        $pending = is_array($queue['pending'] ?? null) ? $queue['pending'] : [];
        if ($active === [] && $pending === []) {
            return '';
        }
        $list = function (array $items) use ($h): string {
            if ($items === []) {
                return '<p><em>aucun</em></p>';
            }
            $lis = '';
            foreach ($items as $it) {
                $u = is_array($it) ? (string) ($it['url'] ?? '') : (string) $it;
                $lis .= '<li>' . $h($u) . '</li>';
            }
            return '<ul style="margin:4px 0;">' . $lis . '</ul>';
        };
        return "<h3>File d'attente</h3>"
            . '<p><strong>En cours (' . count($active) . ') :</strong></p>' . $list($active)
            . '<p><strong>En attente (' . count($pending) . ') :</strong></p>' . $list($pending);
    }

    /** Version texte de la file d'attente. Chaîne vide si rien. */
    private function queueText(array $queue): string
    {
        $active  = is_array($queue['active']  ?? null) ? $queue['active']  : [];
        $pending = is_array($queue['pending'] ?? null) ? $queue['pending'] : [];
        if ($active === [] && $pending === []) {
            return '';
        }
        $fmt = function (array $items): array {
            $out = [];
            foreach ($items as $it) {
                $out[] = '    - ' . (is_array($it) ? (string) ($it['url'] ?? '') : (string) $it);
            }
            return $out;
        };
        $lines = ['  En cours (' . count($active) . ') :'];
        $lines = array_merge($lines, $active === [] ? ['    (aucun)'] : $fmt($active));
        $lines[] = '  En attente (' . count($pending) . ') :';
        $lines = array_merge($lines, $pending === [] ? ['    (aucun)'] : $fmt($pending));
        return implode(PHP_EOL, $lines);
    }

    private function resolveClientIp(array $server): string
    {
        $forwarded = trim((string) ($server['HTTP_X_FORWARDED_FOR'] ?? ''));
        if ($forwarded !== '') {
            return trim(explode(',', $forwarded)[0]);
        }
        return trim((string) ($server['REMOTE_ADDR'] ?? 'unknown'));
    }

    private function error(string $code, string $message): array
    {
        return ['ok' => false, 'error_code' => $code, 'message' => $message];
    }
}
