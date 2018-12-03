#!/usr/bin/env python

#  Copyright (c) 2018 Eclipse KUKSA project
#
#  This program and the accompanying materials are made available under the
#  terms of the Eclipse Public License 2.0 which is available at
#  http://www.eclipse.org/legal/epl-2.0
#
#  SPDX-License-Identifier: EPL-2.0
#
#  Contributors: Robert Bosch GmbH

import json
import os
import subprocess

from requests import Session, HTTPError

DEFAULT_SERVER = 'http://localhost:8080'
DEFAULT_USERNAME = 'admin'
DEFAULT_PASSWORD = 'admin'


def create_app(config_file, upload_image=False, server=DEFAULT_SERVER, username=DEFAULT_USERNAME, password=DEFAULT_PASSWORD):
    with open(config_file, mode='r') as __config_file:
        config = json.load(__config_file)

    image_file = None
    if upload_image:
        image_file = '{}-{}.tar'.format(config['name'], config['version'])
        success = subprocess.run('docker save {} > {}'.format(config['image'], image_file), shell=True).returncode

        if success != 0:
            print("Failed to save the docker image")
            exit(1)

    http = Session()
    http.auth = (username, password)

    # create HawkBit app

    app_response = http.post(
        url='{}/rest/v1/softwaremodules'.format(server),
        json=[
            dict(
                type='application',
                name=config['name'],
                version=config['version'],
            )
        ]
    )
    __handle_error(app_response)

    app = json.loads(app_response.content)[0]
    app_id = app.get('id')

    # upload the config artifact

    config_response = http.post(
        url='{}/rest/v1/softwaremodules/{}/artifacts'.format(server, app_id),
        data={
            'filename': 'docker-container.json',
        },
        files={
            'file': open(config_file, mode='rb')
        },
    )
    __handle_error(config_response)

    # upload the docker image artifact

    if image_file:
        image_response = http.post(
            url='{}/rest/v1/softwaremodules/{}/artifacts'.format(server, app_id),
            data={
                'filename': 'docker-image.tar',
            },
            files={
                'file': open(image_file, mode='rb')
            },
        )
        __handle_error(image_response)

        os.remove(image_file)


def __handle_error(response):
    try:
        response.raise_for_status()
    except HTTPError as error:
        content = response.content
        if content:
            content = json.loads(content)
            error = content.get('message')
        print(error)
        exit(1)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Creates a HawkBit application')
    parser.add_argument('config_file', help="JSON file")
    parser.add_argument('-u', '--upload-image', action='store_true', default=False, help="upload the docker image to HawkBit")

    args = parser.parse_args()

    create_app(args.config_file, upload_image=args.upload_image)
