from django.db import migrations

# Common documents an actual Philippine barangay office issues. Not
# exhaustive (DocumentType.__doc__ mentions "23 kinds" as an illustrative
# figure, not a literal target), but a realistic starting catalog an
# admin can extend or edit from the DocumentType management UI --
# get_or_create by code, so this is safe to run against a database that
# already has some of these (e.g. added by hand before this migration
# existed) without duplicating them.
#
# fee=0 on Certificate of Indigency, First Time Jobseeker Certificate,
# Certificate of No Income, and the Solo Parent Certification is not an
# oversight -- those are legally fee-exempt documents in the Philippines
# (RA 11261 for first-time jobseekers; indigency/no-income/solo-parent
# certifications are customarily issued free as they gate access to
# other social services).
DOCUMENT_TYPES = [
    {
        "code": "BRGY-CLR",
        "name": "Barangay Clearance",
        "fee": "50.00",
        "template_body": (
            "This is to certify that {{ resident.full_name }}, "
            "{{ resident.get_civil_status_display|lower }}, of legal age, and a "
            "resident of {{ resident.address }}, is known to this office to be "
            "of good moral character and has no derogatory record on file in "
            "this barangay as of the date of this certification.\n\n"
            "This certification is issued upon the request of the above-named "
            "person for {{ purpose }}."
        ),
    },
    {
        "code": "BRGY-COR",
        "name": "Certificate of Residency",
        "fee": "50.00",
        "template_body": (
            "This is to certify that {{ resident.full_name }} is a bona fide "
            "resident of {{ resident.address }}"
            "{% if resident.purok_or_sitio %}, {{ resident.purok_or_sitio }}{% endif %}, "
            "this barangay.\n\n"
            "This certification is issued upon the request of the above-named "
            "person for {{ purpose }}."
        ),
    },
    {
        "code": "BRGY-IND",
        "name": "Certificate of Indigency",
        "fee": "0.00",
        "template_body": (
            "This is to certify that {{ resident.full_name }}, a resident of "
            "{{ resident.address }}, belongs to an indigent family in this "
            "barangay and does not have sufficient income to meet his/her "
            "family's basic needs.\n\n"
            "This certification is issued upon the request of the above-named "
            "person for {{ purpose }}."
        ),
    },
    {
        "code": "BRGY-BIZ",
        "name": "Barangay Business Clearance",
        "fee": "100.00",
        "template_body": (
            "This is to certify that the business/establishment operated by "
            "{{ resident.full_name }}, located at {{ resident.address }}, is "
            "hereby granted clearance to operate within the jurisdiction of "
            "this barangay, subject to compliance with all existing barangay "
            "ordinances and regulations.\n\n"
            "This clearance is issued for {{ purpose }}."
        ),
    },
    {
        "code": "BRGY-GMC",
        "name": "Certificate of Good Moral Character",
        "fee": "50.00",
        "template_body": (
            "This is to certify that {{ resident.full_name }}, a resident of "
            "{{ resident.address }}, is personally known to this office to be "
            "a person of good moral character and reputation, and has not "
            "been involved in any activity contrary to law, morals, good "
            "customs, or public order.\n\n"
            "This certification is issued upon the request of the above-named "
            "person for {{ purpose }}."
        ),
    },
    {
        "code": "BRGY-NPC",
        "name": "Certificate of No Pending Case",
        "fee": "50.00",
        "template_body": (
            "This is to certify that {{ resident.full_name }}, a resident of "
            "{{ resident.address }}, has no pending case filed against him/her "
            "before this barangay as of the date of this certification.\n\n"
            "This certification is issued upon the request of the above-named "
            "person for {{ purpose }}."
        ),
    },
    {
        "code": "BRGY-CERT",
        "name": "Barangay Certification (General Purpose)",
        "fee": "50.00",
        "template_body": (
            "This is to certify that {{ resident.full_name }}, a resident of "
            "{{ resident.address }}, is known to this office based on "
            "available barangay records.\n\n"
            "This certification is issued upon the request of the above-named "
            "person for {{ purpose }}."
        ),
    },
    {
        "code": "BRGY-FTJ",
        "name": "First Time Jobseeker Certificate",
        "fee": "0.00",
        "template_body": (
            "This is to certify that {{ resident.full_name }}, a resident of "
            "{{ resident.address }}, is a first-time jobseeker availing of "
            "the benefits under Republic Act No. 11261, otherwise known as "
            "the \"First Time Jobseekers Assistance Act.\"\n\n"
            "This certification is issued free of charge for {{ purpose }}."
        ),
    },
    {
        "code": "BRGY-COH",
        "name": "Certificate of Cohabitation",
        "fee": "50.00",
        "template_body": (
            "This is to certify that {{ resident.full_name }}, a resident of "
            "{{ resident.address }}, is known to this office to have been "
            "cohabiting with his/her partner as husband and wife for a "
            "considerable length of time.\n\n"
            "This certification is issued upon the request of the above-named "
            "person for {{ purpose }}."
        ),
    },
    {
        "code": "BRGY-NOI",
        "name": "Certificate of No Income",
        "fee": "0.00",
        "template_body": (
            "This is to certify that {{ resident.full_name }}, a resident of "
            "{{ resident.address }}, has no source of income as verified by "
            "this barangay.\n\n"
            "This certification is issued upon the request of the above-named "
            "person for {{ purpose }}."
        ),
    },
    {
        "code": "BRGY-SPC",
        "name": "Solo Parent Certification",
        "fee": "0.00",
        "template_body": (
            "This is to certify that {{ resident.full_name }}, a resident of "
            "{{ resident.address }}, is known to this office to be a solo "
            "parent as defined under Republic Act No. 8972, the \"Solo "
            "Parents' Welfare Act,\" as amended.\n\n"
            "This certification is issued upon the request of the above-named "
            "person for {{ purpose }}."
        ),
    },
    {
        "code": "BRGY-COA",
        "name": "Certificate of Ownership (Animal)",
        "fee": "30.00",
        "template_body": (
            "This is to certify that {{ resident.full_name }}, a resident of "
            "{{ resident.address }}, is the registered owner of the "
            "animal/livestock described in the records of this barangay.\n\n"
            "This certification is issued upon the request of the above-named "
            "person for {{ purpose }}."
        ),
    },
]


def seed_document_types(apps, schema_editor):
    DocumentType = apps.get_model("documents", "DocumentType")
    for entry in DOCUMENT_TYPES:
        DocumentType.objects.get_or_create(
            code=entry["code"],
            defaults={
                "name": entry["name"],
                "template_body": entry["template_body"],
                "fee": entry["fee"],
                "is_active": True,
            },
        )


def noop_reverse(apps, schema_editor):
    # Deliberately not deleting these on reverse -- an admin may have
    # already issued real documents against them, or edited their
    # wording; a migration rollback shouldn't destroy either.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0003_issueddocument_body_text_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_document_types, noop_reverse),
    ]
