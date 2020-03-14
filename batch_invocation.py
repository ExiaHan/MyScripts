#!/usr/bin/python3
# -*- coding: utf-8 -*-

# @Author  : exiahan@exiahan.com
# @Time    : 2020/03/14
# @File    : batch_invocation.py


import sys
import os
import subprocess
import shutil

import logging

DIFF_PATH = '/bin/diff'
BINDIFF_PATH = '/bin/bindiff'
IDAT_PATH = '/bin/idat'
IDAT64_PATH = '/bin/idat64'
ASM_SUFFIX = '.asm'
IDB_SUFFIX = '.idb'
BINEXPORT_SUFFIX = '.BinExport'
BINDIFF_SUFFIX = '.BinDiff'
ASM_DIFFER_SUFFIX = '.diff'
IDA_ENV = dict(os.environ)
IDA_ENV['TVHEADLESS'] = '1'


log = logging.getLogger("IDA_BATCHING")
logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        log.error("[Usage]: %s BINARY1_ABSPATH BINARY2_ABSPATH RESULT_DIRECTORY" % sys.argv[0].split('/')[-1])
        exit(-2)
    if not os.path.exists(DIFF_PATH):
        log.error('[Dependency]: %s not found' %DIFF_PATH)
        exit(-1)
    if not os.path.exists(BINDIFF_PATH):
        log.error('[Dependency]: %s not found' %BINDIFF_PATH)
        exit(-1)
    if not os.path.exists(IDAT_PATH) and os.path.exists(IDAT64_PATH):
        log.error('[Dependency]: %s and %s not found' %(IDAT_PATH, IDAT64_PATH))
        exit(-1)
    primary_binary_path = os.path.abspath(os.path.expanduser(sys.argv[1]))
    secondary_binary_path = os.path.abspath(os.path.expanduser(sys.argv[2]))

    result_directory = os.path.abspath(os.path.expanduser(sys.argv[3]))

    if os.path.exists(result_directory):
        log.info(result_directory + ' exist, now clear it first')
        shutil.rmtree(result_directory)

    os.makedirs(result_directory)

    primary_binary = os.path.basename(primary_binary_path)
    secondary_binary = os.path.basename(secondary_binary_path)
    log.info('Process to differ %s and %s' %(primary_binary, secondary_binary))
    log.info('Path is %s and %s' %(primary_binary_path, secondary_binary_path))

    # TODO: Choose to use idat or idat64 based on file type

    # Basic process, after this we get .idb and .asm
    log.info('Basic process')
    log.info('Process %s' % primary_binary)
    batch_command = [IDAT_PATH, '-B', primary_binary_path]
    # import pdb
    # pdb.set_trace()
    p = subprocess.Popen(batch_command, env=IDA_ENV)
    return_code = p.wait(600)
    if return_code != 0:
        log.error('Failed to process %s' % primary_binary)
        exit(-1)

    log.info('Process %s' % secondary_binary)
    batch_command = [IDAT_PATH, '-B', secondary_binary_path]
    p = subprocess.Popen(batch_command, env=IDA_ENV)
    return_code = p.wait(600)
    if return_code != 0:
        log.error('Failed to process %s' % secondary_binary_path)
        exit(-1)

    # BinDiff process, after this we get .BinExport and .BinDiff(SQLite DB) result
    log.info('Generate BinExport file for %s' % primary_binary)
    bindiff_command = [IDAT_PATH]
    bindiff_command.append('-OBinExportModule:' + primary_binary_path + BINEXPORT_SUFFIX)
    bindiff_command.append('-OBinExportAlsoLogToStdErr:TRUE')
    bindiff_command.append('-OBinExportAutoAction:BinExportBinary')
    bindiff_command.append(primary_binary_path + IDB_SUFFIX)
    p = subprocess.Popen(bindiff_command, env=IDA_ENV)
    return_code = p.wait(600)
    if return_code != 0:
        log.error('Failed generate BinExport for %s' %primary_binary)

    log.info('Generate BinExport file for %s' % secondary_binary)
    bindiff_command = [IDAT_PATH]
    bindiff_command.append('-OBinExportModule:' + secondary_binary_path + BINEXPORT_SUFFIX)
    bindiff_command.append('-OBinExportAlsoLogToStdErr:TRUE')
    bindiff_command.append('-OBinExportAutoAction:BinExportBinary')
    bindiff_command.append(secondary_binary_path + IDB_SUFFIX)
    p = subprocess.Popen(bindiff_command, env=IDA_ENV)
    return_code = p.wait(600)
    if return_code != 0:
        log.error('Failed generate BinExport for %s' %secondary_binary)

    log.info('Begin to generate diff')
    diff_command = [DIFF_PATH]
    diff_command.append(primary_binary_path + ASM_SUFFIX)
    diff_command.append(secondary_binary_path + ASM_SUFFIX)
    diff_output_file = result_directory + '/diff_result' + ASM_DIFFER_SUFFIX
    with open(diff_output_file,'w+') as result_file:
        p = subprocess.Popen(diff_command, env=IDA_ENV, stdout=result_file)
        return_code = p.wait(600)
        if return_code != 0 and return_code != 1:
            log.error('Failed to generate asm diff result')
            exit(-3)

    log.info('Begin to generate BinDiff')
    diff_command = [BINDIFF_PATH]
    diff_command.append(primary_binary_path + BINEXPORT_SUFFIX)
    diff_command.append(secondary_binary_path + BINEXPORT_SUFFIX)
    diff_command.append('--output_dir=' + result_directory)
    p = subprocess.Popen(diff_command, env=IDA_ENV)
    return_code = p.wait(1000)
    if return_code != 0:
        log.error('Failed to generate BinDiff SQLite result')
        exit(-3)
    original_name = result_directory + '/' + primary_binary + '_vs_' + secondary_binary + BINDIFF_SUFFIX
    target_name = result_directory + '/bindiff_result' + BINDIFF_SUFFIX
    os.rename(original_name, target_name)
