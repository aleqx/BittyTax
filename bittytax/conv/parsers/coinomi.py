# -*- coding: utf-8 -*-
# (c) aleqx on github

from decimal import Decimal

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser

WALLET = "Coinomi"

def parse_coinomi(data_row, _parser, _filename):
    in_row = data_row.in_row
    wallet = '%s - %s' % (WALLET, in_row[1])
    coin = in_row[5]
    # patch Coinomi's time export which is missing the seconds
    if len(in_row[10].split(':')) == 2:
        in_row[10] = in_row[10][0:16] + ':' + in_row[9][-2:] + 'Z'

    data_row.timestamp = DataParser.parse_timestamp(in_row[10], tz='UTC')

    if Decimal(in_row[4]) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[4],
                                                 buy_asset=coin,
                                                 wallet=wallet)
    else:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[4])+Decimal(in_row[6])),
                                                 sell_asset=coin,
                                                 fee_asset=coin,
                                                 fee_quantity=in_row[6],
                                                 wallet=wallet)

DataParser(DataParser.TYPE_WALLET,
           WALLET,
           ['Asset', 'AccountName', 'Address', 'AddressName', 'Value',  # 0-4
            'Symbol', 'Fees', 'InternalTransfer', 'TransactionID', 'Time(UTC)',  # 5-9
            'Time(ISO8601-UTC)', 'BlockExplorer'],  # 10-11
           worksheet_name=WALLET,
           row_handler=parse_coinomi)
