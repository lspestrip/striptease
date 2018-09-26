# -*- encoding: utf-8 -*-

'''
Functions to load files from different formats

This module provides a number of functions that are able to load timestreams
from several origins:

1. Local files, either in text or HDF5 format

2. Local/remote URLS, either pointing to JSON information or to HDF5 files

To load datasets, you should stick with "load_timestream", which will
automatically detect the type of file and load it accordingly. Other
functions can be used if you are sure of the exact type of file you're
dealing with.
'''

from collections import namedtuple
import os
from shutil import copyfileobj
from tempfile import NamedTemporaryFile
import urllib.parse as urlparse
import urllib.request as urlreq

import h5py
import numpy as np
import json


def download_json_from_url(url):
    'Return a dictionary containing the data loaded from a JSON link'

    response = urlreq.urlopen(url)
    json_text = response.read().decode('utf-8')
    return json.loads(json_text)


def download_test(url, test_info, output_file):
    'Copy the HDF5 file related to some test into file object "output_file"'

    download_url = urlparse.urljoin(url, test_info['download_url'])
    response = urlreq.urlopen(download_url)
    copyfileobj(response, output_file)


Timestream = namedtuple('Timestream', [
    'time_s',
    'pctime',
    'phb',
    'record',
    'demodulated',
    'power',
    'rfpower_db',
    'freq_hz',
])
Timestream.__doc__ = '''A time stream acquired from one polarimeter.

This is a read-only named tuple with the following fields:

1. "time_s" - Time in seconds

2. "pctime" - On-board time, in clock ticks

3. "phb" - Phase of the slow phase switch

4. "record" - Unknown

5. "demodulated" - 4×N matrix containing the output of DEM0, DEM1, DEM2, DEM3

6. "power" - 4×N matrix containing the output of PWR0, PWR1, PWR2, PWR3

7. "rfpower_db" - Power of the radiofrequency generator, in dB, or -1 if turned
   off

8. "freq_hz" - Frequency of the signal injected by the radiofrequency generator,
   in Hertz. If the generator is turned off, this is -1.
'''


def load_text_file(file_path):
    '''Load a text file into a Timestream object

    Return a timestream object'''

    full_data = np.loadtxt(file_path, skiprows=1)
    return Timestream(
        time_s=np.arange(full_data.shape[0]) / 25.0,
        pctime=full_data[:, 0],
        phb=full_data[:, 1],
        record=full_data[:, 2],
        demodulated=full_data[:, 3:7],
        power=full_data[:, 7:11],
        rfpower_db=full_data[:, 11],
        freq_hz=full_data[:, 12],
    )


def load_hdf5_file(input_file):
    '''Load an HDF5 file into a Timestream object

    Return a 2-tuple containing a dictionary of metadata and a Timestream
    object'''

    with h5py.File(input_file) as h5_file:
        if 'time_series' in h5_file:
            dataset = h5_file['time_series']
            return dict(h5_file.attrs.items()), Timestream(
                time_s=dataset['time_s'].astype(np.float),
                pctime=dataset['pctime'].astype(np.float),
                phb=dataset['phb'].astype(np.int),
                record=dataset['record'].astype(np.int),
                demodulated=np.vstack([dataset[x].astype(np.float) for x in (
                    'dem_Q1_ADU',
                    'dem_U1_ADU',
                    'dem_U2_ADU',
                    'dem_Q2_ADU')]).transpose(),
                power=np.vstack([dataset[x].astype(np.float) for x in (
                    'pwr_Q1_ADU',
                    'pwr_U1_ADU',
                    'pwr_U2_ADU',
                    'pwr_Q2_ADU')]).transpose(),
                rfpower_db=dataset['rfpower_dB'].astype(np.float),
                freq_hz=dataset['freq_Hz'].astype(np.float),
            )
        else:
            return None, None


def load_metadata(url):
    '''Return a dictionary containing the metadata for a test.

    The "url" must point to the JSON record of the test.'''

    req = urlreq.urlopen(url)
    content_type = req.info().get_content_type()

    assert content_type == 'application/json'
    return json.loads(req.read().decode('utf-8'))


def load_timestream(file_path):
    '''Load a time stream from either a text file, HDF5 file, or URL

    The argument "file_path" can be one of the following:

    1. A path to a text file;

    2. A path to an HDF5 file;

    3. An URL pointing to the JSON record of a test;

    4. An URL pointing to an HDF5 file.

    Return a pair consisting of a dictionary containing the medatada and a
    Timestream object.'''

    if not urlreq.splittype(file_path)[0]:
        # Local path
        ext = os.path.splitext(file_path)[1]
        if ext.lower() == '.txt':
            return None, load_text_file(file_path)
        else:
            return load_hdf5_file(file_path)
    else:
        # URL
        req = urlreq.urlopen(file_path)
        content_type = req.info().get_content_type()

        # We are *forced* to create a named temporary file and close it
        # before reading, because h5py does not support reading from
        # file-like objects like BytesIO or an already opened TemporaryFile
        with NamedTemporaryFile(suffix='h5', delete=False) as h5_file:
            h5_file_name = h5_file.name
            if content_type == 'application/json':
                metadata = json.loads(req.read().decode('utf-8'))
                download_test(file_path, metadata, h5_file)
            elif content_type == 'application/hdf5':
                copyfileobj(req, h5_file)
            else:
                raise ValueError(
                    'unknown content type: "{0}"'.format(content_type))

        result = load_hdf5_file(h5_file_name)[1]
        os.remove(h5_file_name)
        return metadata, result
