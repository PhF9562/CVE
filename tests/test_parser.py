"""Tests du parseur de texte OCR."""

import unittest

from cartevisite.parser import (
    extract_email,
    extract_phone,
    extract_website,
    normalize_phone,
    parse_contact,
)


class TestFieldExtractors(unittest.TestCase):
    def test_extract_email(self):
        self.assertEqual(extract_email("Contact: Jean.Dupont@Example.COM"), "jean.dupont@example.com")
        self.assertEqual(extract_email("aucun email ici"), "")

    def test_extract_phone_formats(self):
        self.assertEqual(extract_phone("Tel: +33 6 12 34 56 78"), "+33612345678")
        self.assertEqual(extract_phone("06.12.34.56.78"), "0612345678")
        self.assertEqual(extract_phone("(514) 555-0199"), "5145550199")

    def test_extract_phone_ignores_short_numbers(self):
        self.assertEqual(extract_phone("Bureau 12"), "")

    def test_normalize_phone(self):
        self.assertEqual(normalize_phone("+33 (0)6-12-34"), "+330612 34".replace(" ", ""))
        self.assertEqual(normalize_phone("01 23 45"), "012345")
        self.assertEqual(normalize_phone("texte"), "")

    def test_extract_website_skips_email_domain(self):
        text = "jean@acme.com\nwww.acme.com"
        email = extract_email(text)
        self.assertEqual(extract_website(text, email), "www.acme.com")

    def test_extract_website_plain(self):
        self.assertEqual(extract_website("Visitez https://exemple.fr/contact"), "https://exemple.fr/contact")


class TestParseContact(unittest.TestCase):
    def test_full_card(self):
        text = (
            "Jean Dupont\n"
            "Directeur Commercial\n"
            "ACME SARL\n"
            "Tel: +33 6 12 34 56 78\n"
            "jean.dupont@acme.com\n"
            "www.acme.com\n"
        )
        contact = parse_contact(text)
        self.assertEqual(contact.full_name, "Jean Dupont")
        self.assertEqual(contact.title, "Directeur Commercial")
        self.assertEqual(contact.company, "ACME SARL")
        self.assertEqual(contact.phone, "+33612345678")
        self.assertEqual(contact.email, "jean.dupont@acme.com")
        self.assertEqual(contact.website, "www.acme.com")
        self.assertEqual(contact.raw_text, text)

    def test_company_by_uppercase(self):
        text = "Marie Martin\nGLOBEX\nmarie@globex.io"
        contact = parse_contact(text)
        self.assertEqual(contact.company, "GLOBEX")
        self.assertEqual(contact.full_name, "Marie Martin")

    def test_title_keyword_english(self):
        text = "John Smith\nChief Technology Officer\nInitech Inc\njohn@initech.com"
        contact = parse_contact(text)
        self.assertIn("Officer", contact.title)
        self.assertEqual(contact.company, "Initech Inc")

    def test_empty_text(self):
        contact = parse_contact("")
        self.assertTrue(contact.is_empty())

    def test_labels_are_stripped(self):
        text = "Email : test@site.fr\nTéléphone : 01 02 03 04 05"
        contact = parse_contact(text)
        self.assertEqual(contact.email, "test@site.fr")
        self.assertEqual(contact.phone, "0102030405")


if __name__ == "__main__":
    unittest.main()
