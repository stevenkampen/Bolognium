#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, random, string, array, logging
import urllib2,urllib

import base64
import bolognium.lib.aes as aes
from bolognium.ext.config import get_config

key = get_config(u'aes_key') # u'TisG!7nrPMb8S3&QnyHSJT@?LEr7hAmv'
iv = get_config(u'aes_iv') # u'BsKzU5QkqC5d4Gvn'

def encrypt(string):
  """Encrypts the string with key and iv above"""
  return base64.b64encode(encryptData(key, iv, string))

def decrypt(string):
  """Decrypts the string with key and iv above"""
  return decryptData(key, iv, base64.b64decode(string))

def encryptData(key, iv, data, mode=aes.AESModeOfOperation.modeOfOperation["CFB"]):
    """encrypt `data` using `key`

    `key` should be a string of bytes.

    returned cipher is a string of bytes prepended with the initialization
    vector.

    """
    key = map(ord, key)
    keysize = len(key)
    assert keysize in aes.AES.keySize.values(), 'invalid key size: %s' % keysize
    # create a new iv using random data
    iv = [ord(i) for i in iv]
    moo = aes.AESModeOfOperation()
    (mode, length, ciph) = moo.encrypt(data, mode, key, keysize, iv)
    return ''.join(map(chr, ciph))

def decryptData(key, iv, data, mode=aes.AESModeOfOperation.modeOfOperation["CFB"]):
    """decrypt `data` using `key`

    `key` should be a string of bytes.

    `data` should have the initialization vector prepended as a string of
    ordinal values.

    """

    key = map(ord, key)
    keysize = len(key)
    assert keysize in aes.AES.keySize.values(), 'invalid key size: %s' % keysize
    iv = [ord(i) for i in iv]
    data = map(ord, data)
    moo = aes.AESModeOfOperation()
    decr = moo.decrypt(data, None, mode, key, keysize, iv)
    return decr
