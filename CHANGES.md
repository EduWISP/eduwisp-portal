# Changelog — eduwisp-portal

## Non rilasciato / Unreleased

- Prototipo v0 (ADR-0018): pagine per dirigente, docente e famiglia; area dell'amministratore di sistema con gli istituti; menu «Vedi come» in sola lettura, con avviso, motivo e registrazione in eduwisp-audit; accessi fuori ambito 404 e registrati; scelta del ruolo per chi ne ha più di uno. / *v0 prototype: head teacher, teacher and family pages; platform admin area; read-only audited "view as".*
- Famiglia: per i figli maggiorenni senza consenso il portale mostra solo che sono maggiorenni, senza dati (ADR-0018). / *Adult children without consent: name and notice only.*
- App consentite (ADR-0019): nella pagina della classe le app consentite e gli sblocchi attivi; il docente sblocca un'app per la lezione e la richiude, solo nelle sue classi. Nuova dipendenza: eduwisp-apps. / *Allowed apps on the class page; teachers unlock and relock apps for their classes.*
- Account in sola lettura (gruppo `sola-lettura`, per esempio l'utente «demo» dell'ambiente di prova): vede tutto e può usare il «vedi come», ma ogni modifica è rifiutata. / *Read-only accounts (e.g. the demo user).*
- Loghi delle app e segno «obbligatoria» nella pagina della classe (ADR-0020). / *App logos and required badge on the class page.*
