from socrata import Socrata
from socrata.authorization import Authorization
from test.auth import auth, TestCase

class TestSource(TestCase):
    def test_create_source(self):
        rev = self.create_rev()
        source = rev.create_upload('foo.csv')
        self.assertEqual(source.attributes['source_type']['filename'], 'foo.csv')

        assert 'show' in source.list_operations()
        assert 'bytes' in source.list_operations()


    def test_upload_blob(self):
        rev = self.create_rev()
        source = rev.create_upload('foo.csv')

        with open('test/fixtures/simple.csv', 'rb') as f:
            source = source.blob(f)
            self.assertEqual(source.attributes['parse_options']['parse_source'], False)
            rev = rev.show()
            self.assertEqual(rev.attributes['blob_id'], source.attributes['id'])


    def test_upload_csv(self):
        rev = self.create_rev()
        source = rev.create_upload('foo.csv')

        with open('test/fixtures/simple.csv', 'rb') as f:
            source = source.csv(f)
            print("Done now???")
            output_schema = source.get_latest_input_schema().get_latest_output_schema()
            output_schema = output_schema.wait_for_finish()

            names = sorted([ic['field_name'] for ic in output_schema.attributes['output_columns']])
            self.assertEqual(['a', 'b', 'c'], names)

            assert 'show' in output_schema.list_operations()


    def test_upload_kml(self):
        rev = self.create_rev()
        source = rev.create_upload('simple_points.kml')

        with open('test/fixtures/simple_points.kml', 'rb') as f:
            source = source.kml(f)
            input_schema = source.get_latest_input_schema()
            self.assertEqual(
                set(['point', 'a_float', 'a_string', 'a_num', 'a_bool']),
                set([ic['field_name'] for ic in input_schema.attributes['input_columns']])
            )

    def test_upload_shapefile(self):
        rev = self.create_rev()
        source = rev.create_upload('wards.zip')

        with open('test/fixtures/wards.zip', 'rb') as f:
            source = source.shapefile(f)
            input_schema = source.get_latest_input_schema()
            self.assertEqual(
                set(['ward_phone', 'ward', 'shape_leng', 'shape_area', 'perimeter', 'hall_phone', 'hall_offic', 'edit_date1', 'data_admin', 'class', 'alderman', 'address', 'the_geom']),
                set([ic['field_name'] for ic in input_schema.attributes['input_columns']])
            )

    def test_upload_geojson(self):
        rev = self.create_rev()
        source = rev.create_upload('simple_points.geojson')
        with open('test/fixtures/simple_points.geojson', 'rb') as f:
            source = source.geojson(f)
            input_schema = source.get_latest_input_schema()
            self.assertEqual(
                set(['point', 'a_float', 'a_string', 'a_num', 'a_bool']),
                set([ic['field_name'] for ic in input_schema.attributes['input_columns']])
            )

    def test_create_from_url(self):
        # Yes, this is a bad idea
        # But the reason this test doesn't make a view on demand is because
        # we blacklist local addresses, which wouldn't allow this test to run against
        # localhost
        url = 'https://cheetah.test-socrata.com/api/views/agi2-jsej/rows.csv?accessType=DOWNLOAD'

        rev = self.create_rev()
        source = rev.source_from_url(url)

        source = source.wait_for_finish()

        output_schema = source.get_latest_input_schema().get_latest_output_schema()
        output_schema.wait_for_finish()

        actual_columns = set([oc['field_name'] for oc in output_schema.attributes['output_columns']])
        expected_columns = set(['id', 'plausibility', 'incident_occurrence', 'incident_location', 'witness_gibberish', 'blood_alcohol_level'])

        self.assertEqual(actual_columns, expected_columns)

    def test_create_source_outside_rev(self):
        pub = Socrata(auth)

        source = pub.sources.create_upload('foo.csv')
        self.assertEqual(source.attributes['source_type']['filename'], 'foo.csv')

        assert 'show' in source.list_operations()
        assert 'bytes' in source.list_operations()

    def test_upload_csv_outside_rev(self):
        pub = Socrata(auth)
        source = pub.sources.create_upload('foo.csv')

        with open('test/fixtures/simple.csv', 'rb') as f:
            source = source.csv(f)
            input_schema = source.get_latest_input_schema()
            names = sorted([ic['field_name'] for ic in input_schema.attributes['input_columns']])
            self.assertEqual(['a', 'b', 'c'], names)

    def test_put_source_in_revision(self):
        pub = Socrata(auth)

        source = pub.sources.create_upload('foo.csv')
        with open('test/fixtures/simple.csv', 'rb') as f:
            source = source.csv(f)
            input_schema = source.get_latest_input_schema()
            rev = self.create_rev()
            source = source.add_to_revision(rev)


    def test_source_change_header_rows(self):
        pub = Socrata(auth)
        source = pub.sources.create_upload('foo.csv')

        source = source\
            .change_parse_option('header_count').to(2)\
            .change_parse_option('column_header').to(2)\
            .run()

        po = source.attributes['parse_options']
        self.assertEqual(po['header_count'], 2)
        self.assertEqual(po['column_header'], 2)

    def test_source_change_on_existing_upload(self):
        pub = Socrata(auth)
        source = pub.sources.create_upload('foo.csv')

        with open('test/fixtures/skip-header.csv', 'rb') as f:
            source = source.csv(f)


        source = source\
            .change_parse_option('header_count').to(2)\
            .change_parse_option('column_header').to(2)\
            .run()

        source = source.wait_for_finish()

        po = source.attributes['parse_options']
        self.assertEqual(po['header_count'], 2)
        self.assertEqual(po['column_header'], 2)

        input_schema = source.get_latest_input_schema()
        output_schema = input_schema.latest_output()

        [a, b, c] = output_schema.attributes['output_columns']

        self.assertEqual(a['field_name'], 'a')
        self.assertEqual(b['field_name'], 'b')
        self.assertEqual(c['field_name'], 'c')
