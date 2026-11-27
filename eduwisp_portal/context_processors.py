# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
from .middleware import is_read_only_account
from .vista import RUOLI, appartenenze, vista_corrente


def portale(request):
    """Vista corrente e voci del menu «Vedi come» per i template del portale."""
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}
    vista = vista_corrente(request)
    return {
        "vista": vista,
        "sola_lettura": is_read_only_account(request.user),
        "mie_appartenenze": [] if vista.vedi_come else appartenenze(request.user),
        "ruoli_vedi_come": [(r, etichetta) for r, (etichetta, _) in RUOLI.items()],
    }
