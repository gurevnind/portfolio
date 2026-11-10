#!/usr/bin/env python3
"""Выкладка dist/ в бакет Yandex Object Storage (S3-совместимый API).

  export AWS_ACCESS_KEY_ID=...        # статический ключ сервисного аккаунта
  export AWS_SECRET_ACCESS_KEY=...
  python3 deploy_yc.py --dry-run      # показать, что изменится
  python3 deploy_yc.py                # загрузить изменения и удалить лишнее

Загружаются только изменившиеся файлы (сверка по MD5). Каждому объекту
выставляются Content-Type и Cache-Control — бакет отдаёт их как заголовки.
"""
import argparse
import hashlib
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from boto3.s3.transfer import TransferConfig

ROOT = Path(__file__).resolve().parent
DIST = ROOT / 'dist'
ENDPOINT = 'https://storage.yandexcloud.net'
REGION = 'ru-central1'
DEFAULT_BUCKET = 'gurevnind.ru'

# Служебные файлы других хостингов в бакет не нужны.
SKIP = {'_headers'}

TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.txt': 'text/plain; charset=utf-8',
    '.xml': 'application/xml; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.svg': 'image/svg+xml',
    '.webp': 'image/webp',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.ico': 'image/x-icon',
    '.pdf': 'application/pdf',
}

# Без multipart ETag объекта равен MD5 файла — по нему и сверяем изменения.
SINGLE_PART = TransferConfig(multipart_threshold=512 * 1024 * 1024)

REVALIDATE = 'public, max-age=0, must-revalidate'
IMMUTABLE = 'public, max-age=31536000, immutable'


def cache_control(key):
    # Картинки и site.<хэш>.js не меняются под тем же именем; PDF и HTML — могут.
    if key.startswith('assets/') and not key.endswith('.pdf'):
        return IMMUTABLE
    return REVALIDATE


def local_files():
    files = {}
    for p in sorted(DIST.rglob('*')):
        if p.is_file() and not p.is_symlink() and p.name not in SKIP:
            files[p.relative_to(DIST).as_posix()] = p
    return files


def md5(path):
    return hashlib.md5(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--bucket', default=DEFAULT_BUCKET)
    ap.add_argument('--dry-run', action='store_true', help='только показать изменения')
    args = ap.parse_args()

    if not DIST.is_dir():
        sys.exit('Нет папки dist/ — сначала запустите build.py')
    if not (os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('AWS_SECRET_ACCESS_KEY')):
        sys.exit('Задайте AWS_ACCESS_KEY_ID и AWS_SECRET_ACCESS_KEY (статический ключ сервисного аккаунта)')

    s3 = boto3.client('s3', endpoint_url=ENDPOINT, region_name=REGION)

    remote = {}
    try:
        for page in s3.get_paginator('list_objects_v2').paginate(Bucket=args.bucket):
            for obj in page.get('Contents', []):
                remote[obj['Key']] = obj['ETag'].strip('"')
    except ClientError as e:
        err = e.response.get('Error', {})
        sys.exit(f'Object Storage отказал ({err.get("Code")}): {err.get("Message")}\n'
                 'Проверьте ключи, имя бакета и роль storage.editor у сервисного аккаунта.')

    local = local_files()
    unknown = sorted({Path(k).suffix for k in local} - set(TYPES))
    if unknown:
        sys.exit(f'Неизвестные расширения, добавьте их в TYPES: {", ".join(unknown)}')

    upload = [k for k, p in local.items() if remote.get(k) != md5(p)]
    delete = sorted(set(remote) - set(local))

    # HTML последним: страницы не должны ссылаться на ещё не загруженные файлы.
    upload.sort(key=lambda k: (k.endswith('.html'), k))
    for key in upload:
        print(('upload ' if key in remote else 'add    ') + key)
        if not args.dry_run:
            s3.upload_file(str(local[key]), args.bucket, key, ExtraArgs={
                'ContentType': TYPES[Path(key).suffix],
                'CacheControl': cache_control(key),
            }, Config=SINGLE_PART)
    for key in delete:
        print('delete ' + key)
    if delete and not args.dry_run:
        for i in range(0, len(delete), 1000):
            s3.delete_objects(Bucket=args.bucket, Delete={'Objects': [{'Key': k} for k in delete[i:i + 1000]]})

    print(f'{"[dry-run] " if args.dry_run else ""}{len(upload)} загружено, {len(delete)} удалено, '
          f'{len(local) - len(upload)} без изменений — бакет {args.bucket}')


if __name__ == '__main__':
    main()
