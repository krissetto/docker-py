from unittest import mock

import pytest

import docker
from docker import auth

from . import fake_api
from .api_test import (
    DEFAULT_TIMEOUT_SECONDS,
    BaseAPIClientTest,
    fake_request,
    fake_resolve_authconfig,
    url_prefix,
)


class ImageTest(BaseAPIClientTest):
    def test_image_viz(self):
        with pytest.raises(Exception):  # noqa: B017
            self.client.images('busybox', viz=True)
            self.fail('Viz output should not be supported!')

    def test_images(self):
        self.client.images(all=True)

        fake_request.assert_called_with(
            'GET',
            f"{url_prefix}images/json",
            params={'only_ids': 0, 'all': 1},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_images_name(self):
        self.client.images('foo:bar')

        fake_request.assert_called_with(
            'GET',
            f"{url_prefix}images/json",
            params={'only_ids': 0, 'all': 0,
                    'filters': '{"reference": ["foo:bar"]}'},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_images_quiet(self):
        self.client.images(all=True, quiet=True)

        fake_request.assert_called_with(
            'GET',
            f"{url_prefix}images/json",
            params={'only_ids': 1, 'all': 1},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_image_ids(self):
        self.client.images(quiet=True)

        fake_request.assert_called_with(
            'GET',
            f"{url_prefix}images/json",
            params={'only_ids': 1, 'all': 0},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_images_filters(self):
        self.client.images(filters={'dangling': True})

        fake_request.assert_called_with(
            'GET',
            f"{url_prefix}images/json",
            params={'only_ids': 0, 'all': 0,
                    'filters': '{"dangling": ["true"]}'},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_pull(self):
        self.client.pull('joffrey/test001')

        args = fake_request.call_args
        assert args[0][1] == f"{url_prefix}images/create"
        assert args[1]['params'] == {
            'tag': 'latest', 'fromImage': 'joffrey/test001'
        }
        assert not args[1]['stream']

    def test_pull_stream(self):
        self.client.pull('joffrey/test001', stream=True)

        args = fake_request.call_args
        assert args[0][1] == f"{url_prefix}images/create"
        assert args[1]['params'] == {
            'tag': 'latest', 'fromImage': 'joffrey/test001'
        }
        assert args[1]['stream']

    def test_commit(self):
        self.client.commit(fake_api.FAKE_CONTAINER_ID)

        fake_request.assert_called_with(
            'POST',
            f"{url_prefix}commit",
            data='{}',
            headers={'Content-Type': 'application/json'},
            params={
                'repo': None,
                'comment': None,
                'tag': None,
                'container': fake_api.FAKE_CONTAINER_ID,
                'author': None,
                'pause': True,
                'changes': None
            },
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_remove_image(self):
        self.client.remove_image(fake_api.FAKE_IMAGE_ID)

        fake_request.assert_called_with(
            'DELETE',
            f"{url_prefix}images/{fake_api.FAKE_IMAGE_ID}",
            params={'force': False, 'noprune': False},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_image_history(self):
        self.client.history(fake_api.FAKE_IMAGE_NAME)

        fake_request.assert_called_with(
            'GET',
            f"{url_prefix}images/test_image/history",
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_import_image(self):
        self.client.import_image(
            fake_api.FAKE_TARBALL_PATH,
            repository=fake_api.FAKE_REPO_NAME,
            tag=fake_api.FAKE_TAG_NAME
        )

        fake_request.assert_called_with(
            'POST',
            f"{url_prefix}images/create",
            params={
                'repo': fake_api.FAKE_REPO_NAME,
                'tag': fake_api.FAKE_TAG_NAME,
                'fromSrc': fake_api.FAKE_TARBALL_PATH
            },
            data=None,
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_import_image_from_bytes(self):
        stream = (i for i in range(0, 100))

        self.client.import_image(
            stream,
            repository=fake_api.FAKE_REPO_NAME,
            tag=fake_api.FAKE_TAG_NAME
        )

        fake_request.assert_called_with(
            'POST',
            f"{url_prefix}images/create",
            params={
                'repo': fake_api.FAKE_REPO_NAME,
                'tag': fake_api.FAKE_TAG_NAME,
                'fromSrc': '-',
            },
            headers={
                'Content-Type': 'application/tar',
            },
            data=stream,
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_import_image_from_image(self):
        self.client.import_image(
            image=fake_api.FAKE_IMAGE_NAME,
            repository=fake_api.FAKE_REPO_NAME,
            tag=fake_api.FAKE_TAG_NAME
        )

        fake_request.assert_called_with(
            'POST',
            f"{url_prefix}images/create",
            params={
                'repo': fake_api.FAKE_REPO_NAME,
                'tag': fake_api.FAKE_TAG_NAME,
                'fromImage': fake_api.FAKE_IMAGE_NAME
            },
            data=None,
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_inspect_image(self):
        self.client.inspect_image(fake_api.FAKE_IMAGE_NAME)

        fake_request.assert_called_with(
            'GET',
            f"{url_prefix}images/test_image/json",
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_inspect_image_undefined_id(self):
        for arg in None, '', {True: True}:
            with pytest.raises(docker.errors.NullResource) as excinfo:
                self.client.inspect_image(arg)

            assert excinfo.value.args[0] == 'Resource ID was not provided'

    def test_push_image(self):
        with mock.patch('docker.auth.resolve_authconfig',
                        fake_resolve_authconfig):
            self.client.push(fake_api.FAKE_IMAGE_NAME)

        fake_request.assert_called_with(
            'POST',
            f"{url_prefix}images/test_image/push",
            params={
                'tag': None
            },
            data='{}',
            headers={'Content-Type': 'application/json'},
            stream=False,
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_push_image_with_tag(self):
        with mock.patch('docker.auth.resolve_authconfig',
                        fake_resolve_authconfig):
            self.client.push(
                fake_api.FAKE_IMAGE_NAME, tag=fake_api.FAKE_TAG_NAME
            )

        fake_request.assert_called_with(
            'POST',
            f"{url_prefix}images/test_image/push",
            params={
                'tag': fake_api.FAKE_TAG_NAME,
            },
            data='{}',
            headers={'Content-Type': 'application/json'},
            stream=False,
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_push_image_with_auth(self):
        auth_config = {
            'username': "test_user",
            'password': "test_password",
            'serveraddress': "test_server",
        }
        encoded_auth = auth.encode_header(auth_config)
        self.client.push(
            fake_api.FAKE_IMAGE_NAME, tag=fake_api.FAKE_TAG_NAME,
            auth_config=auth_config
        )

        fake_request.assert_called_with(
            'POST',
            f"{url_prefix}images/test_image/push",
            params={
                'tag': fake_api.FAKE_TAG_NAME,
            },
            data='{}',
            headers={'Content-Type': 'application/json',
                     'X-Registry-Auth': encoded_auth},
            stream=False,
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_push_image_stream(self):
        with mock.patch('docker.auth.resolve_authconfig',
                        fake_resolve_authconfig):
            self.client.push(fake_api.FAKE_IMAGE_NAME, stream=True)

        fake_request.assert_called_with(
            'POST',
            f"{url_prefix}images/test_image/push",
            params={
                'tag': None
            },
            data='{}',
            headers={'Content-Type': 'application/json'},
            stream=True,
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_tag_image(self):
        self.client.tag(fake_api.FAKE_IMAGE_ID, fake_api.FAKE_REPO_NAME)

        fake_request.assert_called_with(
            'POST',
            f"{url_prefix}images/{fake_api.FAKE_IMAGE_ID}/tag",
            params={
                'tag': None,
                'repo': 'repo',
                'force': 0
            },
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_tag_image_tag(self):
        self.client.tag(
            fake_api.FAKE_IMAGE_ID,
            fake_api.FAKE_REPO_NAME,
            tag=fake_api.FAKE_TAG_NAME
        )

        fake_request.assert_called_with(
            'POST',
            f"{url_prefix}images/{fake_api.FAKE_IMAGE_ID}/tag",
            params={
                'tag': 'tag',
                'repo': 'repo',
                'force': 0
            },
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_tag_image_force(self):
        self.client.tag(
            fake_api.FAKE_IMAGE_ID, fake_api.FAKE_REPO_NAME, force=True)

        fake_request.assert_called_with(
            'POST',
            f"{url_prefix}images/{fake_api.FAKE_IMAGE_ID}/tag",
            params={
                'tag': None,
                'repo': 'repo',
                'force': 1
            },
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_get_image(self):
        self.client.get_image(fake_api.FAKE_IMAGE_ID)

        fake_request.assert_called_with(
            'GET',
            f"{url_prefix}images/{fake_api.FAKE_IMAGE_ID}/get",
            stream=True,
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_load_image(self):
        self.client.load_image('Byte Stream....')

        fake_request.assert_called_with(
            'POST',
            f"{url_prefix}images/load",
            data='Byte Stream....',
            stream=True,
            params={},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_load_image_quiet(self):
        self.client.load_image('Byte Stream....', quiet=True)

        fake_request.assert_called_with(
            'POST',
            f"{url_prefix}images/load",
            data='Byte Stream....',
            stream=True,
            params={'quiet': True},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )
