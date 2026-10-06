"""Route tests. The service layer is patched out, so these need no database."""

import io
import logging
import re
import unittest
from unittest.mock import patch

import requests
from sqlalchemy.exc import IntegrityError

from app import create_app
from app.routes import creative_routes
from app.services import crud


def setUpModule():
    # The error handlers log on purpose; keep that out of the test output.
    logging.disable(logging.CRITICAL)


def tearDownModule():
    logging.disable(logging.NOTSET)


def make_client():
    with patch('app.init_db'):
        app = create_app()
    app.testing = False  # keep the error handlers active, as in production
    return app.test_client()


class RouteTestCase(unittest.TestCase):
    def setUp(self):
        self.client = make_client()


class RequestBodyTest(RouteTestCase):
    def test_post_without_a_body_is_a_400(self):
        response = self.client.post('/ad')
        self.assertEqual(response.status_code, 400)
        self.assertIn('JSON object', response.get_json()['error'])

    def test_post_with_a_json_list_is_a_400(self):
        response = self.client.post('/campaign', json=[1, 2, 3])
        self.assertEqual(response.status_code, 400)

    def test_put_with_malformed_json_is_a_400(self):
        response = self.client.put('/publisher', data='{not json', content_type='application/json')
        self.assertEqual(response.status_code, 400)

    @patch('app.routes.ad_routes.create_ad', return_value={'adid': 'AD1'})
    def test_valid_post_reaches_the_service(self, create_ad):
        response = self.client.post('/ad', json={'adname': 'x'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()['ad'], {'adid': 'AD1'})
        create_ad.assert_called_once_with({'adname': 'x'})


class StateChangeTest(RouteTestCase):
    def test_unknown_state_is_a_400(self):
        response = self.client.patch('/ad?ad_id=AD1&state=BOGUS')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'error': 'Invalid state'})

    def test_missing_state_is_a_400(self):
        self.assertEqual(self.client.patch('/ad?ad_id=AD1').status_code, 400)

    def test_nothing_can_go_back_to_created(self):
        response = self.client.patch('/campaign?campaign_id=C1&state=CREATED')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'error': 'Invalid State Transition'})

    @patch('app.routes.ad_routes.update_ad_state', return_value=False)
    def test_unknown_id_is_a_404(self, update):
        response = self.client.patch('/ad?ad_id=missing&state=ACTIVE')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {'error': 'Ad not found'})
        update.assert_called_once_with('missing', 'ACTIVE')

    @patch('app.routes.ad_unit_routes.update_ad_unit_state', return_value=True)
    def test_success_message_uses_the_entity_label(self, update):
        response = self.client.patch('/adunit?ad_unit_id=ADU1&state=INACTIVE')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'message': 'Ad unit state updated successfully to INACTIVE'})

    def test_every_entity_rejects_a_bad_state_the_same_way(self):
        for path in ('/ad?ad_id=1', '/campaign?campaign_id=1', '/creative?creative_id=1',
                     '/adunit?ad_unit_id=1', '/publisher?publisher_id=1', '/advertiser?advertiser_id=1'):
            with self.subTest(path=path):
                response = self.client.patch(path + '&state=NOPE')
                self.assertEqual(response.status_code, 400)


class ListByStateTest(RouteTestCase):
    def test_every_entity_rejects_an_unknown_state(self):
        for entity in ('ad', 'campaign', 'creative', 'adunit', 'publisher', 'advertiser'):
            with self.subTest(entity=entity):
                self.assertEqual(self.client.get(f'/{entity}/state/NOPE').status_code, 400)

    @patch('app.routes.campaign_routes.get_campaign_by_state', return_value=[{'campaignid': 'C1'}])
    def test_valid_state_returns_the_rows(self, fetch):
        response = self.client.get('/campaign/state/ACTIVE')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [{'campaignid': 'C1'}])
        fetch.assert_called_once_with('ACTIVE')


class LookupTest(RouteTestCase):
    @patch('app.routes.publisher_routes.get_publisher_by_id', return_value=None)
    def test_unknown_publisher_is_a_404(self, _):
        response = self.client.get('/publisher/publisherid/missing')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {'error': 'Publisher not found'})

    @patch('app.routes.ad_unit_routes.get_ad_unit_by_publisher', return_value=[])
    def test_publisher_with_no_ad_units_is_a_404(self, _):
        self.assertEqual(self.client.get('/adunit/publisher/P1').status_code, 404)

    @patch('app.routes.ad_routes.update_ad', return_value=None)
    def test_updating_an_unknown_ad_is_a_404(self, _):
        self.assertEqual(self.client.put('/ad', json={'adid': 'missing'}).status_code, 404)


class ErrorHandlerTest(RouteTestCase):
    @patch('app.routes.ad_routes.create_ad')
    def test_integrity_error_is_a_400(self, create_ad):
        create_ad.side_effect = IntegrityError('INSERT ...', {}, Exception('null value in column "campaignid"'))
        response = self.client.post('/ad', json={'adname': 'x'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.get_json())

    @patch('app.routes.ad_routes.get_all_ads', side_effect=RuntimeError('boom'))
    def test_unexpected_error_is_json_500_without_details(self, _):
        response = self.client.get('/ad')
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json(), {'error': 'Internal server error'})

    def test_unknown_route_is_json_404(self):
        response = self.client.get('/nope')
        self.assertEqual(response.status_code, 404)
        self.assertIn('error', response.get_json())

    def test_wrong_method_keeps_the_allow_header(self):
        response = self.client.delete('/ad')
        self.assertEqual(response.status_code, 405)
        self.assertIn('GET', response.headers['Allow'])
        self.assertIn('error', response.get_json())

    def test_health_check(self):
        self.assertEqual(self.client.get('/health').get_json(), {'status': 'ok'})


class CreativeUploadTest(RouteTestCase):
    def upload(self, **kwargs):
        return self.client.post(
            '/creative/upload?filename=banner.png',
            data={'image': (io.BytesIO(b'png bytes'), 'banner.png')},
            content_type='multipart/form-data',
            **kwargs,
        )

    def test_not_configured_is_a_503(self):
        with patch.object(creative_routes, 'SUPABASE_URL', ''):
            self.assertEqual(self.upload().status_code, 503)

    def test_unreachable_storage_is_a_502(self):
        with patch.object(creative_routes, 'SUPABASE_URL', 'http://storage.test'), \
                patch.object(creative_routes, 'SUPABASE_KEY', 'key'), \
                patch('app.routes.creative_routes.requests.post', side_effect=requests.ConnectionError):
            response = self.upload()
        self.assertEqual(response.status_code, 502)

    def test_a_reply_that_is_not_json_is_a_400_not_a_crash(self):
        reply = requests.Response()
        reply.status_code = 502
        reply._content = b'<html>bad gateway</html>'
        with patch.object(creative_routes, 'SUPABASE_URL', 'http://storage.test'), \
                patch.object(creative_routes, 'SUPABASE_KEY', 'key'), \
                patch('app.routes.creative_routes.requests.post', return_value=reply):
            response = self.upload()
        self.assertEqual(response.status_code, 400)

    def test_success_returns_the_public_url(self):
        reply = requests.Response()
        reply.status_code = 200
        reply._content = b'{"Key": "Creatives/banner.png"}'
        with patch.object(creative_routes, 'SUPABASE_URL', 'http://storage.test'), \
                patch.object(creative_routes, 'SUPABASE_KEY', 'key'), \
                patch('app.routes.creative_routes.requests.post', return_value=reply):
            response = self.upload()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()['image_url'],
            'http://storage.test/storage/v1/object/public/Creatives/banner.png',
        )

    def test_path_tricks_in_the_filename_are_stripped(self):
        with patch.object(creative_routes, 'SUPABASE_URL', 'http://storage.test'),                 patch.object(creative_routes, 'SUPABASE_KEY', 'key'),                 patch('app.routes.creative_routes.upload_image_to_supabase', return_value={'Key': 'ok'}) as upload:
            response = self.client.post(
                '/creative/upload?filename=../../etc/passwd',
                data={'image': (io.BytesIO(b'x'), 'x.png')},
                content_type='multipart/form-data',
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(upload.call_args[0][1], 'etc_passwd')


class ReportingTest(RouteTestCase):
    @patch('app.routes.reporting_routes.get_report', return_value=[{'_id': 'AD1', 'click': 2, 'render': 5}])
    def test_reports_are_returned_as_json(self, _):
        response = self.client.get('/reports')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()[0]['click'], 2)

    @patch('app.routes.reporting_routes.delete_report_by_ad_id', return_value=False)
    def test_deleting_a_missing_report_is_a_404(self, _):
        self.assertEqual(self.client.delete('/reports/AD9').status_code, 404)


class GenerateIdTest(unittest.TestCase):
    def test_id_has_prefix_timestamp_and_random_suffix(self):
        self.assertRegex(crud.generate_id('AD'), r'^AD\d{17}[0-9a-f]{4}$')

    def test_ids_made_in_the_same_millisecond_do_not_collide(self):
        with patch('app.services.crud.time.time', return_value=1_700_000_000.123):
            ids = {crud.generate_id('C') for _ in range(500)}
        self.assertGreater(len(ids), 490)

    def test_prefixes_stay_distinct(self):
        self.assertFalse(re.match(r'^CR', crud.generate_id('C')))


if __name__ == '__main__':
    unittest.main()
