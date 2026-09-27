import contextlib
import io
import json
import os
import subprocess
import shutil
import stat
import ssl
import uuid
import unittest
import urllib.error
from unittest.mock import patch, MagicMock

import main


@contextlib.contextmanager
def temporary_repository():
    root = os.path.dirname(os.path.abspath(__file__))
    directory = os.path.abspath(os.path.join(root, 'test-tmp-' + uuid.uuid4().hex))
    assert os.path.commonpath([root, directory]) == root
    os.mkdir(directory, 0o777)
    try:
        yield directory
    finally:
        def retry_readonly(function, path, error):
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            function(path)
        shutil.rmtree(directory, onerror=retry_readonly)


class OutputTests(unittest.TestCase):
    def test_pr_sections_and_title_limit(self):
        raw = json.dumps({'title': '가' * 100, 'why': ['배경'], 'what': ['변경'], 'how_to_test': ['확인']})
        data = main.parse_output(raw, 'pr')
        self.assertEqual(len(data['title']), 80)
        output = main.render_output(data, 'pr')
        for heading in ['Why', 'What', 'How to Test']:
            self.assertIn('## ' + heading + '\n- ', output)

    def test_invalid_output_rejected(self):
        for raw in ['invalid', '[]', '{"title":""}', '{"title":"제목","why":[],"what":["변경"],"how_to_test":["확인"]}']:
            with self.subTest(raw=raw), self.assertRaises(main.AppError):
                main.parse_output(raw, 'pr')

    def test_commit_optional_body(self):
        self.assertEqual(main.parse_output('{"title":"fix: 오류 수정"}', 'commit')['body'], [])

    def test_safe_mode_masks_and_limits(self):
        text = 'api_key="private-value"\ntest@example.com\nsk-example123\n' + 'changed\n' * 250
        context = main.prepare_context(' M config', text, True, 'active-secret')
        for secret in ['private-value', 'test@example.com', 'sk-example123']:
            self.assertNotIn(secret, context)
        self.assertIn('200줄 제한', context)
        self.assertNotIn('active-secret', main.prepare_context('active-secret', 'active-secret', False, 'active-secret'))


class GitTests(unittest.TestCase):
    def test_clean_staged_and_unstaged(self):
        previous = os.getcwd()
        with temporary_repository() as directory:
            try:
                os.chdir(directory)
                subprocess.run(['git', 'init', '-q'], check=True)
                self.assertEqual(main.collect_changes(), ('', ''))
                with open('sample.txt', 'w') as stream:
                    stream.write('staged content\n')
                with self.assertRaises(main.AppError):
                    main.collect_changes()
                subprocess.run(['git', 'add', 'sample.txt'], check=True)
                with open('sample.txt', 'a') as stream:
                    stream.write('unstaged content\n')
                status, diff = main.collect_changes()
                self.assertIn('sample.txt', status)
                self.assertIn('+staged content', diff)
                self.assertIn('+unstaged content', diff)
                os.mkdir('other')
                with open('other/unrelated.txt', 'w') as stream:
                    stream.write('unrelated change\n')
                subprocess.run(['git', 'add', 'other'], check=True)
                scoped_status, scoped_diff = main.collect_changes('sample.txt')
                self.assertNotIn('unrelated', scoped_status + scoped_diff)
                self.assertIn('+unstaged content', scoped_diff)
            finally:
                os.chdir(previous)


class APITests(unittest.TestCase):
    def test_certificate_error_is_identified(self):
        with patch('main.urllib.request.build_opener') as build:
            build.return_value.open.side_effect = urllib.error.URLError(
                ssl.SSLCertVerificationError(1, 'certificate verify failed'))
            with self.assertRaisesRegex(main.AppError, 'TLS 인증서 검증 실패'):
                main.call_api('https://example.com/chat', 'key', 'model', 0.2, 100, [])

    def test_success_payload_and_single_call(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {'choices': [{'message': {'content': '{"title":"fix: 수정"}'}}]}
        ).encode()
        with patch('main.urllib.request.build_opener') as build:
            build.return_value.open.return_value = response
            result = main.call_api('https://example.com/chat', 'key', 'model', 0.2, 100, [])
            self.assertIn('title', result)
            build.return_value.open.assert_called_once()
            request = build.return_value.open.call_args.args[0]
            self.assertEqual(json.loads(request.data)['max_tokens'], 100)

    def test_auth_error_does_not_echo_server_body(self):
        with patch('main.urllib.request.build_opener') as build:
            build.return_value.open.side_effect = urllib.error.HTTPError('https://example.com', 401, 'secret', {}, None)
            with self.assertRaisesRegex(main.AppError, '인증 실패'):
                main.call_api('https://example.com/chat', 'key', 'model', 0.2, 100, [])
            build.return_value.open.assert_called_once()

    def test_no_changes_skips_api_without_key(self):
        with patch('main.collect_changes', return_value=('', '')), patch('main.call_api') as api:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main.main(['commit']), 0)
            api.assert_not_called()


if __name__ == '__main__':
    unittest.main()
