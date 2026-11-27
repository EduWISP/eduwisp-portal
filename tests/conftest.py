# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from eduwisp_school.models import (
    Guardian,
    SchoolClass,
    SchoolLevel,
    SchoolYear,
    Section,
    Site,
    Student,
    StudentEnrollment,
    TeachingAssignment,
)
from eduwisp_users.models import Membership, Organization, Role

User = get_user_model()


@pytest.fixture
def scuola(db):
    """Istituto inventato: sezioni A e B, classi 1A e 1B, un docente su A, una famiglia."""
    org = Organization.objects.create(name="Liceo Fittizio", slug="liceo")
    sede = Site.objects.create(organization=org, name="Sede", level=SchoolLevel.SECONDARIA_2)
    anno = SchoolYear.objects.create(
        organization=org,
        label="2026/2027",
        start_date=date(2026, 9, 1),
        end_date=date(2027, 6, 30),
        is_current=True,
    )
    a = Section.objects.create(organization=org, site=sede, name="A")
    b = Section.objects.create(organization=org, site=sede, name="B")
    c1a = SchoolClass.objects.create(organization=org, school_year=anno, section=a, year_number=1)
    c1b = SchoolClass.objects.create(organization=org, school_year=anno, section=b, year_number=1)

    def studente(nome, classe):
        s = Student.objects.create(organization=org, display_name=nome)
        StudentEnrollment.objects.create(organization=org, student=s, school_class=classe)
        return s

    figlio, altro = studente("Rossi Anna", c1a), studente("Bianchi Luca", c1b)

    def persona(username, ruolo):
        u = User.objects.create_user(username, first_name=username.title())
        m = Membership.objects.create(user=u, organization=org, role=ruolo)
        return u, m

    preside, m_preside = persona("preside", Role.SCHOOL_ADMIN)
    docente, m_docente = persona("docente", Role.TEACHER)
    genitore, m_genitore = persona("genitore", Role.GUARDIAN)
    TeachingAssignment.objects.create(
        organization=org, teacher=docente, school_year=anno, section=a, subject="Matematica"
    )
    Guardian.objects.create(organization=org, user=genitore, student=figlio, is_primary=True)
    return {
        "org": org,
        "c1a": c1a,
        "c1b": c1b,
        "figlio": figlio,
        "altro": altro,
        "preside": preside,
        "docente": docente,
        "genitore": genitore,
        "m_preside": m_preside,
        "m_docente": m_docente,
        "m_genitore": m_genitore,
    }


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser("admin", password="x")
