#!/usr/bin/env python3

"""Command-line interface to MediaFire Simple File Sharing and Storage"""

import argparse
import logging
import os
import sys

from pprint import pprint

from mediafire.client import (MediaFireClient,
                              Folder, ResourceNotFoundError)


LOG_FORMAT = '%(levelname)s %(asctime)s %(funcName)s: %(message)s'

logging.basicConfig(format=LOG_FORMAT, level=logging.WARNING)

APP_ID = '42511'


logging.getLogger("mediafire.client").setLevel(logging.INFO)
logging.getLogger(
    "requests.packages.urllib3.connectionpool").setLevel(logging.WARNING)


def do_ls(client, args):
    """List directory"""

    for item in client.get_folder_contents_iter(args.uri):
        # privacy flag
        if item['privacy'] == 'public':
            item['pf'] = '@'
        else:
            item['pf'] = '-'

        if type(item) is Folder:
            # type flag
            item['tf'] = 'd'
            item['key'] = item['folderkey']
            item['size'] = ''
        else:
            item['tf'] = '-'
            item['key'] = item['quickkey']
            item['name'] = item['filename']

        print("{tf}{pf} {key:>15} {size:>10} {created} {name}".format(**item))

    return True


def do_file_upload(client, args):
    """Upload files"""

    # Sanity check
    if len(args.paths) > 1:
        # destination must be a directory
        try:
            resource = client.get_resource_by_uri(args.dest_uri)
        except ResourceNotFoundError:
            resource = None

        if (resource and type(resource) is not Folder
                or not args.dest_uri.endswith('/')):
            print("file-upload: "
                  "target '{}' is not a directory".format(args.dest_uri))
            if not resource:
                print("\tHint: add trailing / to create one")
            return None

    with client.upload_session():
        for src_path in args.paths:
            print("Uploading {} to {}".format(src_path, args.dest_uri))
            result = client.upload_file(src_path, args.dest_uri)

            print("Uploaded {}, result={}".format(src_path, result))

    return True


def do_file_download(client, args):
    """Download file"""

    # Sanity check
    if not os.path.isdir(args.dest_path) and not args.dest_path.endswith('/'):
        print("file-download: "
              "target '{}' is not a directory".format(args.dest_path))
        if not os.path.exists(args.dest_path):
            print("\tHint: add trailing / to create one")
        return None

    for src_uri in args.uris:
        print("Downloading {} to {}".format(src_uri, args.dest_path))
        client.download_file(src_uri, args.dest_path)
        print("Downloaded {}".format(src_uri))

    return True


def do_file_show(client, args):
    """Output file contents to stdout"""
    for src_uri in args.uris:
        client.download_file(src_uri, sys.stdout.buffer)

    return True


def do_folder_create(client, args):
    """Create directory"""
    result = client.create_folder(args.uri, recursive=True)
    print("Result = {}".format(result))

    return True


def do_resource_delete(client, args):
    """Remove resource"""
    client.delete_resource(args.uri, purge=args.purge)
    return True


def do_file_update_metadata(client, args):
    """Update file metadata"""
    client.update_file_metadata(args.uri, filename=args.filename,
                                description=args.description, mtime=args.mtime,
                                privacy=args.privacy)
    return True


def do_folder_update_metadata(client, args):
    """Update file metadata"""
    client.update_folder_metadata(args.uri, foldername=args.foldername,
                                  description=args.description,
                                  mtime=args.mtime, privacy=args.privacy,
                                  privacy_recursive=args.recursive)
    return True


def do_debug_get_resource(client, args):
    """Stat resource"""

    pprint(client.get_resource_by_uri(args.uri))
    return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(prog='mediafire-cli',
                                     description=__doc__)

    parser.add_argument('--debug', dest='debug', action='store_true',
                        default=False, help='Enable debug output')
    parser.add_argument('--email', dest='email', required=False)
    parser.add_argument('--password', dest='password', required=False)

    actions = parser.add_subparsers(title='Actions', dest='action')
    # http://bugs.python.org/issue9253#msg186387
    actions.required = True

    # ls
    subparser = actions.add_parser('ls',
                                   help=do_ls.__doc__)
    subparser.add_argument('uri', nargs='?',
                           help='MediaFire URI',
                           default='mediafire:/')

    # file-upload
    subparser = actions.add_parser('file-upload',
                                   help=do_file_upload.__doc__)
    subparser.add_argument('paths', nargs='+',
                           help='Path[s] to upload')
    subparser.add_argument('dest_uri', help='Destination MediaFire URI')

    # file-download
    subparser = actions.add_parser('file-download',
                                   help=do_file_download.__doc__)
    subparser.add_argument('uris', nargs='+',
                           help='MediaFire File URI[s] to download')
    subparser.add_argument('dest_path', help='Destination path')

    # file-show
    subparser = actions.add_parser('file-show',
                                   help=do_file_show.__doc__)
    subparser.add_argument('uris', nargs='+',
                           help='MediaFire File URI[s] to print out')

    # folder-create
    subparser = actions.add_parser('folder-create',
                                   help=do_folder_create.__doc__)
    subparser.add_argument('uri', help='MediaFire folder path URI')

    # resource-delete
    subparser = actions.add_parser('resource-delete',
                                   help=do_resource_delete.__doc__)
    subparser.add_argument('uri', help='MediaFire resource URI')
    subparser.add_argument('--purge', help="Purge, don't send to trash",
                           dest="purge", action="store_true", default=False)

    # file-update-metadata
    subparser = actions.add_parser('file-update-metadata',
                                   help=do_file_update_metadata.__doc__)
    subparser.add_argument('uri', help='MediaFire file URI')
    subparser.add_argument('--filename', help='Set file name',
                           default=None, dest='filename')
    subparser.add_argument('--privacy', help='Set file privacy',
                           choices=['public', 'private'],
                           default=None, dest='privacy')
    subparser.add_argument('--description',
                           help='Set file description',
                           dest='description', default=None)
    subparser.add_argument('--mtime', help="Set file modification time",
                           dest='mtime', default=None)

    # folder-update-metadata
    subparser = actions.add_parser('folder-update-metadata',
                                   help=do_folder_update_metadata.__doc__)
    subparser.add_argument('uri', help='MediaFire folder URI')
    subparser.add_argument('--foldername', help='Set folder name',
                           default=None, dest='foldername')
    subparser.add_argument('--privacy', help='Set folder privacy',
                           choices=['public', 'private'],
                           default=None, dest='privacy')
    subparser.add_argument('--recursive', help='Set privacy recursively',
                           action='store_true', default=None,
                           dest='recursive')
    subparser.add_argument('--description',
                           help='Set folder description',
                           dest='description', default=None)
    subparser.add_argument('--mtime', help='Set folder mtime',
                           default=None, dest='mtime')

    # debug-get-resource
    subparser = actions.add_parser('debug-get-resource',
                                   help=do_debug_get_resource.__doc__)
    subparser.add_argument('uri', help='MediaFire resource URI',
                           default='mediafire:/', nargs='?')

    args = parser.parse_args()

    if args.debug:
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        logging.getLogger("mediafire.client").setLevel(logging.DEBUG)

    client = MediaFireClient()

    if args.email and args.password:
        client.login(args.email, args.password, app_id=APP_ID)

    router = {
        "file-upload": do_file_upload,
        "file-download": do_file_download,
        "file-show": do_file_show,
        "ls": do_ls,
        "folder-create": do_folder_create,
        "resource-delete": do_resource_delete,
        "file-update-metadata": do_file_update_metadata,
        "folder-update-metadata": do_folder_update_metadata,
        "debug-get-resource": do_debug_get_resource
    }

    if args.action in router:
        result = router[args.action](client, args)

        if not result:
            sys.exit(1)
    else:
        print('Unsupported action: {}'.format(args.action))
        sys.exit(1)

if __name__ == "__main__":
    main()
