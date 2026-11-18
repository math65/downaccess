"""Bilan des echecs d'une file : regrouper par cause, resumer, rapporter.

Demande de Brad (2026-11-16) : une vingtaine d'erreurs dans une grosse file,
aucun rapport envoye parce qu'il fallait les reprendre une par une. Les echecs
simples attendent maintenant la fin de la file ; un seul bilan les presente
regroupes, et un seul rapport (donc un seul mail) les couvre tous.

Logique pure : aucun import wx.
"""
from dataclasses import dataclass, field

from app.core.i18n import _translate as _

# Au-dela, la liste des titres d'une cause devient un pave dans la fenetre.
_MAX_TITLES_SHOWN = 10
# Un journal de diagnostic par cause, pour les causes les plus frequentes
# seulement : chaque journal rejoue un telechargement, et le mail doit rester
# lisible.
MAX_DIAGNOSTICS = 3


@dataclass
class Failure:
    download_id: str
    url: str
    message: str
    title: str = ""
    site: str = ""


@dataclass
class FailureGroup:
    message: str
    failures: list[Failure] = field(default_factory=list)

    @property
    def headline(self) -> str:
        """Premiere ligne du message : la cause, sans les conseils."""
        for line in (self.message or "").splitlines():
            if line.strip():
                return line.strip()
        return ""


def group_failures(failures: list[Failure]) -> list[FailureGroup]:
    """Regroupe par message, la cause la plus frequente d'abord.

    Le message est celui montre a l'utilisateur, deja reformule : deux videos
    retirees donnent le meme texte, alors que leurs erreurs brutes different
    par l'identifiant de la video.
    """
    groups: dict[str, FailureGroup] = {}
    for failure in failures:
        groups.setdefault(failure.message, FailureGroup(failure.message)).failures.append(failure)
    # `sorted` est stable : a egalite, l'ordre d'apparition est conserve.
    return sorted(groups.values(), key=lambda g: -len(g.failures))


def _count_label(count: int) -> str:
    if count == 1:
        return _("1 téléchargement")
    return _("{count} téléchargements").format(count=count)


def summary_text(groups: list[FailureGroup]) -> str:
    """Texte du bilan affiche a l'utilisateur."""
    total = sum(len(g.failures) for g in groups)
    blocks = [_("{count} téléchargements ont échoué.").format(count=total)]
    for group in groups:
        lines = [_("{downloads} — {cause}").format(
            downloads=_count_label(len(group.failures)), cause=group.headline)]
        rest = (group.message or "").split(group.headline, 1)[-1].strip()
        if rest:
            lines.append(rest)
        shown = group.failures[:_MAX_TITLES_SHOWN]
        lines.extend("  " + (f.title or f.url) for f in shown)
        hidden = len(group.failures) - len(shown)
        if hidden > 0:
            lines.append("  " + _("… et {count} autres").format(count=hidden))
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def report_summary(groups: list[FailureGroup]) -> str:
    """Resume court pour l'en-tete du rapport (lu par le developpeur)."""
    total = sum(len(g.failures) for g in groups)
    lines = [f"{total} téléchargements en échec, {len(groups)} cause(s) :"]
    lines.extend(f"- {len(g.failures)} x {g.headline}" for g in groups)
    return "\n".join(lines)


def report_details(groups: list[FailureGroup]) -> str:
    """Toutes les adresses, classees par cause, pour le corps du rapport."""
    blocks = []
    for group in groups:
        lines = [f"{len(group.failures)} x {group.headline}"]
        lines.extend(f"  {f.url or '(adresse inconnue)'}" for f in group.failures)
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def representatives(groups: list[FailureGroup]) -> list[Failure]:
    """Un telechargement par cause a rejouer en diagnostic, les causes les
    plus frequentes d'abord. On prefere un echec dont l'adresse est connue."""
    chosen = []
    for group in groups[:MAX_DIAGNOSTICS]:
        chosen.append(next((f for f in group.failures if f.url), group.failures[0]))
    return chosen


def join_logs(logs: list[tuple[Failure, str]], budget: int) -> str:
    """Assemble les journaux de diagnostic sans depasser `budget` caracteres.

    Chaque journal garde son debut (versions, options) ET sa fin : c'est a la
    fin que yt-dlp ecrit l'erreur, et une simple troncature la perdrait.
    """
    if not logs:
        return ""
    share = max(2000, budget // len(logs) - 200)
    parts = []
    for failure, log in logs:
        log = log or ""
        if len(log) > share:
            half = share // 2
            log = log[:half] + "\n[... journal abrégé ...]\n" + log[-half:]
        parts.append(f"===== {failure.url or '(adresse inconnue)'} =====\n{log}")
    return "\n\n".join(parts)
