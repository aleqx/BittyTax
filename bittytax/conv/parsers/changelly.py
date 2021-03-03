# -*- coding: utf-8 -*-
# (c) aleqx on Github

import sys
import copy
from decimal import Decimal

from colorama import Fore, Back

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

# Currency from
# Currency to
# Status
# Date
# Exchange amount
# Total fee
# Exchange rate
# Receiver
# Amount received

WALLET = "Changelly"

def parse_changelly_all(data_rows, parser, _filename):
    transfer_rows = []
    for data_row in data_rows:
        if data_row.in_row[2] != "finished" and not config.args.unconfirmed:
            sys.stderr.write("%srow[%s] %s\n" % (
                Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))
            sys.stderr.write("%sWARNING%s Skipping unconfirmed transaction, "
                             "use the [-uc] option to include it\n" % (
                                 Back.YELLOW + Fore.BLACK, Back.RESET + Fore.YELLOW))
            continue

        transfer_rows += parse_changelly(data_row, parser, _filename)

    data_rows += transfer_rows

def parse_changelly(data_row, parser, _filename):
    in_row = data_row.in_row

    data_row.timestamp = DataParser.parse_timestamp(in_row[3])

    data_row_deposit = copy.deepcopy(data_row)
    data_row_withdrawal = copy.deepcopy(data_row)

    buy_asset = in_row[1].upper()
    sell_asset = in_row[0].upper()

    data_row_deposit.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                     data_row.timestamp,
                                                     buy_quantity=in_row[4],
                                                     buy_asset=sell_asset,
                                                     wallet=WALLET)

    data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                             data_row.timestamp,
                                             buy_quantity=Decimal(in_row[8]) + Decimal(in_row[5]),
                                             buy_asset=buy_asset,
                                             sell_asset=sell_asset,
                                             sell_quantity=in_row[4],
                                             wallet=WALLET)

    data_row_withdrawal.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                        data_row.timestamp,
                                                        sell_quantity=in_row[8],
                                                        sell_asset=buy_asset,
                                                        fee_asset=buy_asset,
                                                        fee_quantity=in_row[5],
                                                        wallet=WALLET)

    return data_row_deposit, data_row_withdrawal

DataParser(DataParser.TYPE_WALLET,
           WALLET,
           ['Currency from', 'Currency to', 'Status', 'Date',
            'Exchange amount', 'Total fee', 'Exchange rate', 'Receiver', 'Amount received'],
           worksheet_name=WALLET,
           all_handler=parse_changelly_all)
