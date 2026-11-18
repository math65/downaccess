"""Bilan des echecs : regroupement, textes et rapport unique (Brad, 2026-11-16)."""
from app.core import error_reporter
from app.core.error_summary import (
    MAX_DIAGNOSTICS, Failure, group_failures, join_logs, report_details,
    report_summary, representatives, summary_text,
)


def _echecs():
    retirees = [Failure(f"a{i}", f"https://x/a{i}", "Video retiree.\n\nRien a faire.",
                        title=f"Titre a{i}") for i in range(14)]
    refusees = [Failure(f"b{i}", f"https://x/b{i}", "HTTP Error 403") for i in range(6)]
    return [refusees[0], *retirees, *refusees[1:]]


def test_regroupe_par_cause_la_plus_frequente_d_abord():
    groupes = group_failures(_echecs())
    assert [len(g.failures) for g in groupes] == [14, 6]
    assert groupes[0].headline == "Video retiree."


def test_le_bilan_compte_et_abrege_les_longues_listes():
    texte = summary_text(group_failures(_echecs()))
    assert "20" in texte and "14" in texte and "6" in texte
    assert "Rien a faire." in texte, "les conseils du message restent lisibles"
    assert "Titre a0" in texte and "Titre a13" not in texte
    assert "https://x/b0" in texte, "sans titre, l'adresse en tient lieu"


def test_le_rapport_liste_toutes_les_adresses():
    groupes = group_failures(_echecs())
    assert "20" in report_summary(groupes) and "2 cause" in report_summary(groupes)
    details = report_details(groupes)
    assert all(f"https://x/a{i}" in details for i in range(14))
    assert all(f"https://x/b{i}" in details for i in range(6))


def test_un_diagnostic_par_cause_plafonne():
    echecs = [Failure(f"d{i}", f"https://x/{i}", f"cause {i}") for i in range(8)]
    choisis = representatives(group_failures(echecs))
    assert len(choisis) == MAX_DIAGNOSTICS
    # Un echec sans adresse ne peut pas etre rejoue : on en prefere un autre.
    groupes = group_failures([Failure("s", "", "c"), Failure("t", "https://x/t", "c")])
    assert representatives(groupes)[0].download_id == "t"


def test_les_journaux_gardent_leur_fin():
    """C'est a la fin que yt-dlp ecrit l'erreur."""
    logs = [(Failure("a", "https://x/a", "c"), "debut" + "x" * 50_000 + "ERREUR FINALE A"),
            (Failure("b", "https://x/b", "c"), "court")]
    texte = join_logs(logs, 10_000)
    assert len(texte) < 12_000
    assert "ERREUR FINALE A" in texte and "debut" in texte and "court" in texte
    assert "https://x/a" in texte and "https://x/b" in texte


def test_le_rapport_groupe_tient_en_un_seul_envoi():
    groupes = group_failures(_echecs())
    rapport = error_reporter.build_report(
        url="https://x/a0", site="X", format_spec="mp3",
        error_message=report_summary(groupes), verbose_log="journal",
        user_comment="", email="a@b.fr",
        extra_sections={"Échecs regroupés": report_details(groupes)},
        subject_label="20 échecs regroupés")
    assert "20 échecs regroupés" in rapport["subject_hint"]
    assert "https://x/b5" in rapport["sections"]["Échecs regroupés"]
    # Un rapport ordinaire ne change pas.
    simple = error_reporter.build_report(
        url="u", site="X", format_spec="", error_message="e", verbose_log="",
        user_comment="")
    assert "Échecs regroupés" not in simple["sections"]
    assert "— X —" in simple["subject_hint"]
