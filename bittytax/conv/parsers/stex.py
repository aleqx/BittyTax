# -*- coding: utf-8 -*-
# (c) aleqx on github

import re
import sys

from decimal import Decimal
from colorama import Fore, Back

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

# Date
# id
# Type
# Amount
# Fee
# Currency
# Direction
# Trade price
# trade_id
# txid

WALLET = "STEX"

def parse_row(data_row, parser, _filename):
    in_row = data_row.in_row

    data_row.timestamp = DataParser.parse_timestamp(in_row[0])

    if in_row[2] in ("Deposit"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[5],
                                                 wallet=WALLET)

    elif in_row[2] == "Reward":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[5],
                                                 wallet=WALLET)

    elif in_row[2] == "Withdrawal":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=in_row[3],
                                                 sell_asset=in_row[5],
                                                 fee_quantity=in_row[4],
                                                 fee_asset=in_row[5],
                                                 wallet=WALLET)

    elif in_row[2] == "Order":
        coin, base = in_row[5].split('/')
        if in_row[6] == "Sell":
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                     data_row.timestamp,
                                                     sell_quantity=in_row[3],
                                                     sell_asset=coin,
                                                     buy_quantity=round(Decimal(in_row[3]) * Decimal(in_row[7]) - Decimal(0.000000005), 8) - Decimal(in_row[4]),
                                                     buy_asset=base,
                                                     fee_quantity=in_row[4],
                                                     fee_asset=base,
                                                     wallet=WALLET)
        else:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                     data_row.timestamp,
                                                     buy_quantity=Decimal(in_row[3]) - Decimal(in_row[4]),
                                                     buy_asset=coin,
                                                     sell_quantity=round(Decimal(in_row[7]) * Decimal(in_row[3]) - Decimal(0.000000005), 8),
                                                     sell_asset=base,
                                                     fee_quantity=in_row[4],
                                                     fee_asset=coin,
                                                     wallet=WALLET)


    else:
        raise UnexpectedTypeError(2, parser.in_header[2], in_row[2])

DataParser(DataParser.TYPE_EXCHANGE,
           WALLET,
           ['Date', 'id', 'Type', 'Amount', 'Fee', 'Currency', 'Direction', 'Trade price', 'trade_id', 'txid'],
           worksheet_name=WALLET,
           row_handler=parse_row)
