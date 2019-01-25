#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import json


def check_response(resp, caller):
    '''Raise an exception if a JSON response signals an error condition
    '''
    if resp['status'] != 'OK':
        raise RuntimeError(
            'invalid call to "{0}": "{1}"'.format(caller, resp))


def get_slo(config, session, board, polarimeter, register, slo_type, timeout_ms=500):
    '''Query a SLOW parameter through the REST API

    :param Configuration config: Configuration object, used to build the URL for the REST API call
    :param Session session: A Session object built using the Python module "requests"
    :param str board: The board name, either `R`, `O`, `Y`, `G`, `B`, `I`, or `V`
    :param int polarimeter: The 0-based index of the polarimeter within the module
    :param str register: The name of the register to query
    :param str slo_type: Either `BIAS`, `PREAMP`, or `CRYO`

    :returns: A list containing the data queried to the instrument
    '''
    req = json.dumps({
        'board': board,
        'pol': polarimeter,
        'method': 'GET',
        'type': slo_type,
        'base_addr': register,
        'size': 1,
        'timeout': timeout_ms,
    })

    response = session.post(config.get_rest_url('slo'), data=req).json()
    check_response(response, 'get_slo')
    return response['data']


def get_bias(config, session, board, polarimeter, register, timeout_ms=500):
    '''Query a bias through the REST API
    '''
    return get_slo(
        config=config,
        session=session,
        board=board,
        polarimeter=polarimeter,
        register=register,
        slo_type='BIAS',
        timeout_ms=timeout_ms,
    )


def get_cryo(config, session, board, polarimeter, register, timeout_ms=500):
    '''Query a cryogenic housekeeping through the REST API
    '''
    return get_slo(
        config=config,
        session=session,
        board=board,
        polarimeter=polarimeter,
        register=register,
        slo_type='CRYO',
        timeout_ms=timeout_ms,
    )


def set_slo(config, session, board, polarimeter, register, data, slo_type, timeout_ms=500):
    '''Set a SLOW parameter through the REST API
    '''
    req = json.dumps({
        'board': board,
        'pol': polarimeter,
        'method': 'SET',
        'type': slo_type,
        'base_addr': register,
        'data': data,
        'timeout': timeout_ms,
    })

    response = session.post(config.get_rest_url('slo'), data=req).json()
    check_response(response, 'set_slo')
    return response['data']


def set_bias(config, session, board, polarimeter, register, data, timeout_ms=500):
    '''Set a bias through the REST API
    '''
    return set_slo(
        config=config,
        session=session,
        board=board,
        polarimeter=polarimeter,
        register=register,
        data=data,
        slo_type='BIAS',
        timeout_ms=timeout_ms,
    )


def set_cryo(config, session, board, polarimeter, register, data, timeout_ms=500):
    '''Set a cryogenic housekeeping through the REST API
    '''
    return set_slo(
        config=config,
        session=session,
        board=board,
        polarimeter=polarimeter,
        register=register,
        data=data,
        slo_type='CRYO',
        timeout_ms=timeout_ms,
    )
