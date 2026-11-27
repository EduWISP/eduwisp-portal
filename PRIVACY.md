# Privacy — eduwisp-portal

Documento vivo: va aggiornato a ogni modifica che riguarda dati personali. Riferimenti: [Quadro normativo](https://eduwisp.org/docs/sicurezza-privacy/quadro-normativo/), [Requisiti di conformità](https://eduwisp.org/docs/requisiti/requisiti/#requisiti-di-conformità), [ADR-0018](https://eduwisp.org/docs/decisioni/0018-interfaccia-per-ruoli/).

Il modulo **non salva dati propri**: mostra i dati di eduwisp-school ed eduwisp-devices secondo il ruolo, e registra in eduwisp-audit il «vedi come» e gli accessi fuori ambito.

## Regole

- **Minimizzazione per ruolo** (GDPR art. 25): il dirigente vede l'istituto, il docente solo le classi dei propri incarichi, la famiglia solo i propri figli. Controlli sul server, non solo nell'interfaccia.
- **La famiglia non vede gli altri familiari** collegati allo stesso studente (per esempio un genitore con il collegamento disattivato).
- **«Vedi come»**: sola lettura, avviso sempre visibile, inizio e fine registrati, motivo obbligatorio sui dati reali.
- Nella sessione si salvano solo il riferimento all'appartenenza simulata, il motivo e l'ora di inizio.

---

🇬🇧 *The module stores no data of its own. It shows school and device data according to the user's role (teachers: only their classes; families: only their children; families never see other guardians) and records "view as" sessions and out-of-scope accesses in eduwisp-audit.*
