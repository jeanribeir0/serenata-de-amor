import csv
import lzma
import os
import re
from tempfile import NamedTemporaryFile
from urllib.request import urlretrieve

from django.conf import settings
from django.core.management.base import BaseCommand

from jarbas.core.models import Document


class Command(BaseCommand):
    help = 'Load Serenata de Amor datasets into the database'
    suffixes = ('current-year', 'last-year', 'previous-years')

    def add_arguments(self, parser):
        parser.add_argument(
            '--source', '-s', dest='source', default=None,
            help='Data directory of Serenata de Amor (datasets source)'
        )
        parser.add_argument(
            '--drop-documents', '-d', dest='drop', action='store_true',
            help='Drop all existing documents before loading the dataset'
        )
        parser.add_argument(
            '--batch-size', '-b', dest='batch_size', type=int, default=10000,
            help='Number of documents to be created at a time (default: 10000)'
        )

    def handle(self, *args, **options):
        """Create or update records (if they match `document_id`)"""
        print('Starting with {:,} document'.format(Document.objects.count()))

        if options.get('drop', False):
            self.drop_documents()

        source = options['source']
        datasets = self.load_local(source) if source else self.load_remote()
        documents = self.documents_from(datasets)
        self.bulk_create_by(documents, options['batch_size'])

    def load_remote(self):
        """Load documents from Amazon S3"""
        for suffix in self.suffixes:
            url = self.get_url(suffix)
            print("Loading " + url)
            with NamedTemporaryFile() as tmp:
                urlretrieve(url, filename=tmp.name)
                yield tmp.name

    def load_local(self, source):
        """Load documents from local source"""
        for suffix in self.suffixes:
            path = self.get_path(source, suffix)
            if os.path.exists(path):
                print("Loading " + path)
                yield path
            else:
                print(path + " not found")

    def documents_from(self, datasets):
        """
        Receives a generator with the path to the dataset files and returns a
        Document object for each row of each file.
        """
        for dataset in datasets:
            with lzma.open(dataset, mode='rt') as file_handler:
                for index, row in enumerate(csv.DictReader(file_handler)):
                    row['source'] = self.get_suffix(dataset)
                    row['line'] = index + 1
                    yield Document(**self.serialize(row))

    def serialize(self, document):
        """Read the dict generated by DictReader and fix content types"""
        integers = (
            'document_id',
            'congressperson_id',
            'congressperson_document',
            'term',
            'term_id',
            'subquota_number',
            'subquota_group_id',
            'document_type',
            'month',
            'year',
            'installment',
            'batch_number',
            'reimbursement_number',
            'applicant_id'
        )
        for key in integers:
            document[key] = self.to_number(document[key], int)

        floats = (
            'document_value',
            'remark_value',
            'net_value',
            'reimbursement_value'
        )
        for key in floats:
            document[key] = self.to_number(document[key], float)

        if document['issue_date'] == '':
            document['issue_date'] = None

        return document

    def bulk_create_by(self, documents, size):
        batch = list()
        for document in documents:
            batch.append(document)
            if len(batch) == size:
                Document.objects.bulk_create(batch)
                batch = list()
                self.print_count()
        Document.objects.bulk_create(batch)
        self.print_count(permanent=True)

    def drop_documents(self):
        print('Deleting all existing documents')
        Document.objects.all().delete()
        self.print_count(permanent=True)

    @staticmethod
    def get_file_name(suffix):
        return '{date}-{suffix}.xz'.format(
            date=settings.AMAZON_S3_DATASET_DATE,
            suffix=suffix
        )

    def get_url(self, suffix):
        return 'https://{region}.amazonaws.com/{bucket}/{file_name}'.format(
            region=settings.AMAZON_S3_REGION,
            bucket=settings.AMAZON_S3_BUCKET,
            file_name=self.get_file_name(suffix)
        )

    def get_path(self, source, suffix):
        return os.path.join(source, self.get_file_name(suffix))

    @staticmethod
    def get_suffix(path):
        regex = r'^[\d-]{11}(current-year|last-year|previous-years).xz$'
        name = os.path.basename(path)
        match = re.compile(regex).match(name)
        if match:
            return match.group(1)

    @staticmethod
    def to_number(value, type_of_number):
        if type_of_number == int:
            type_of_number = lambda x: int(float(x))
        return 0 if value in ('NaN', '') else type_of_number(value)

    @staticmethod
    def print_count(**kwargs):
        raw_msg = 'Current count: {:,} documents                              '
        msg = raw_msg.format(Document.objects.count())
        end = '\n' if kwargs.get('permanent', False) else '\r'
        print(msg, end=end)
