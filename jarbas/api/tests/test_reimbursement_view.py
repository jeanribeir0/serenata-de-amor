from json import loads

from django.shortcuts import resolve_url
from django.test import TestCase

from jarbas.core.models import Reimbursement
from jarbas.core.tests import sample_reimbursement_data, suspicions


class TestListApi(TestCase):

    def setUp(self):

        data = [
            sample_reimbursement_data.copy(),
            sample_reimbursement_data.copy(),
            sample_reimbursement_data.copy(),
            sample_reimbursement_data.copy()
        ]

        data[1]['document_id'] = 42 * 2
        data[2]['applicant_id'] = 13 * 3
        data[2]['document_id'] = 42 * 3
        data[3]['year'] = 1983
        data[3]['applicant_id'] = 13 * 4
        data[3]['document_id'] = 42 * 4

        for d in data:
            Reimbursement.objects.create(**d)

        self.all = resolve_url('api:reimbursement-list')
        self.by_year = resolve_url('api:reimbursement-by-year-list', year=1970)
        self.by_applicant = resolve_url('api:reimbursement-by-applicant-list', year=1970, applicant_id=13)

    def test_status(self):
        urls = (self.all, self.by_year, self.by_applicant)
        for resp in map(lambda url: self.client.get(url), urls):
            with self.subTest():
                self.assertEqual(200, resp.status_code)

    def test_content_general(self):
        self.assertEqual(4, Reimbursement.objects.count())
        self.assertEqual(4, self._count_results(self.all))

    def test_content_by_year(self):
        self.assertEqual(3, self._count_results(self.by_year))

    def test_content_by_applicant_id(self):
        self.assertEqual(2, self._count_results(self.by_applicant))

    def _count_results(self, url):
        resp = self.client.get(url)
        content = loads(resp.content.decode('utf-8'))
        return len(content.get('results', 0))


class TestRetrieveApi(TestCase):

    def setUp(self):
        Reimbursement.objects.create(**sample_reimbursement_data)
        unique_id = {'year': 1970, 'applicant_id': 13, 'document_id': 42}
        url = resolve_url('api:reimbursement-detail', **unique_id)
        self.resp = self.client.get(url)

    def test_status(self):
        self.assertEqual(200, self.resp.status_code)

    def test_contents(self):
        contents = loads(self.resp.content.decode('utf-8'))
        expected = dict(
            applicant_id=13,
            batch_number=9,
            cnpj_cpf='11111111111111',
            congressperson_document=2,
            congressperson_id=1,
            congressperson_name='Roger That',
            document_id=42,
            document_number='6',
            document_type=7,
            document_value=8.90,
            installment=7,
            issue_date='1970-01-01',
            leg_of_the_trip='8',
            month=1,
            party='Partido',
            passenger='John Doe',
            all_reimbursement_numbers=[10, 11],
            all_reimbursement_values=[12.13, 14.15],
            all_net_values=[1.99, 2.99],
            remark_value=1.23,
            state='UF',
            subquota_description='Subquota description',
            subquota_group_description='Subquota group desc',
            subquota_group_id=5,
            subquota_id=4,
            supplier='Acme',
            term=1970,
            term_id=3,
            total_net_value=4.56,
            total_reimbursement_value=None,
            year=1970,
            probability=0.5,
            suspicions=suspicions
        )
        self.assertEqual(expected, contents)
