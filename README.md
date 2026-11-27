<p align="center"><img src="https://raw.githubusercontent.com/EduWISP/.github/main/branding/eduwisp-mark.svg" alt="EduWISP" height="72"></p>

# eduwisp-portal

**Interfaccia per ruoli** · *Role-based web interface*

Le pagine di EduWISP per **dirigente**, **docente** e **famiglia**, l'area dell'**amministratore di sistema** e il suo menu **«Vedi come»** in sola lettura ([ADR-0018](https://eduwisp.org/docs/decisioni/0018-interfaccia-per-ruoli/)).

> 🧪 **Stato: prototipo v0.** Provalo su [demo.eduwisp.org](https://demo.eduwisp.org) (solo dati fittizi) con utente **`demo`** e password **`demo`**, in sola lettura.

🇬🇧 *Web pages for head teachers, teachers and families, the platform administrator area and a read-only, audited "view as" menu (ADR-0018). **Status: prototype v0.***

## Cosa vede ciascuno / Who sees what

| Ruolo | Pagina | Vede |
|---|---|---|
| Amministratore di sistema | `/amministrazione/` | tutti gli istituti, le impostazioni (amministrazione di Django), il registro delle operazioni, il menu «Vedi come» |
| Dirigente (`school_admin`) | `/preside/` | tutte le classi dell'istituto, studenti e stato dei dispositivi |
| Docente (`teacher`) | `/docente/` | solo le classi dei propri incarichi nell'anno in corso |
| Famiglia (`guardian`) | `/famiglia/` | solo i propri figli e i dispositivi della scuola a loro affidati |

Nella pagina di una classe compaiono le **app consentite**; il docente può **sbloccare un'app** del catalogo per la lezione (da 30 minuti a 4 ore) e richiuderla prima, solo nelle sue classi, con registrazione ([ADR-0019](https://eduwisp.org/docs/decisioni/0019-app-consentite/)).

I permessi si controllano **sul server** in ogni pagina. Un accesso fuori ambito risponde 404 ed è registrato in [`eduwisp-audit`](https://github.com/EduWISP/eduwisp-audit). Chi ha più ruoli (per esempio docente e genitore) sceglie quale usare dal menu in alto.

## «Vedi come»

L'amministratore di sistema sceglie dal menu a tendina un ruolo (dirigente, docente, famiglia) e poi una persona, e vede l'interfaccia come la vede lei:

- **sola lettura**: durante la vista ogni richiesta che modifica qualcosa (anche nell'amministrazione di Django) è rifiutata con 403;
- **avviso sempre visibile** con la persona simulata e il pulsante «Esci dalla vista»;
- **registrazione** di inizio e fine (con la durata) e di ogni accesso fuori ambito;
- **motivo obbligatorio** sui dati reali; facoltativo nell'ambiente di prova (`EDUWISP_ENVIRONMENT_NOTICE` impostato, ADR-0015).

## Installazione / Setup

```python
INSTALLED_APPS += ["eduwisp_audit", "eduwisp_portal"]
MIDDLEWARE += [
    "eduwisp_portal.middleware.SolaLetturaVediComeMiddleware"
]  # dopo sessioni e autenticazione
TEMPLATES[0]["OPTIONS"]["context_processors"] += ["eduwisp_portal.context_processors.portale"]
LOGIN_URL = "eduwisp_portal:accedi"
LOGIN_REDIRECT_URL = "/"
# urls.py
(path("", include("eduwisp_portal.urls")),)
```

Il ruolo [`ansible-eduwisp`](https://github.com/EduWISP/ansible-eduwisp) lo configura da solo.

## Documentazione / Documentation

- Progettazione / Design: <https://eduwisp.org/docs/decisioni/0018-interfaccia-per-ruoli/>
- Mappa dei repository / Repository map: <https://eduwisp.org/docs/architettura/repository/>

## Dipendenze / Dependencies

[`eduwisp-users`](https://github.com/EduWISP/eduwisp-users), [`eduwisp-school`](https://github.com/EduWISP/eduwisp-school), [`eduwisp-devices`](https://github.com/EduWISP/eduwisp-devices), [`eduwisp-audit`](https://github.com/EduWISP/eduwisp-audit), [`eduwisp-apps`](https://github.com/EduWISP/eduwisp-apps)

## Privacy

Dati personali previsti e regole: [PRIVACY.md](PRIVACY.md). Il rispetto della normativa su privacy e minori è un vincolo bloccante ([ADR-0008](https://eduwisp.org/docs/decisioni/0008-conformita-normativa/)).

## Responsabile del modulo / Module owner

Cerchiamo persone che vogliano prendere in carico questo modulo! Proponiti in [Discussions](https://github.com/EduWISP/docs/discussions). / *Want to own this module? Say hi in Discussions.*

## Contribuire / Contributing

Vedi [CONTRIBUTING](https://github.com/EduWISP/.github/blob/main/CONTRIBUTING.md) e il [Codice di condotta](https://github.com/EduWISP/.github/blob/main/CODE_OF_CONDUCT.md). **Mai dati personali reali** di studenti, famiglie o personale.

## Licenza / License

**AGPL-3.0-or-later**, con termini aggiuntivi di attribuzione e tutela del nome (sezione 7): vedi [LICENSE](LICENSE) e [NOTICE.md](NOTICE.md). Chi usa o modifica EduWISP deve sempre indicare «Basato su EduWISP» e non può usare il nome e il logo per versioni modificate. Licenza scelta secondo le [linee guida AgID](https://eduwisp.org/docs/decisioni/0006-licenza/) per il software usato via rete.

*AGPL-3.0-or-later with additional attribution and trademark terms (section 7): see LICENSE and NOTICE.md.*

I contributi richiedono il [DCO](https://github.com/EduWISP/.github/blob/main/CONTRIBUTING.md#dco) (`git commit -s`).
