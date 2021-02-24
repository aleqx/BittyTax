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

# [0] Transaction
# [1] Type
# [2] Currency
# [3] Amount
# [4] Details
# [5] Outstanding
# [6] Loan
# [7] Date / Time


WALLET = "Nexo"

def parse_nexo(data_row, parser, _filename):
    # fix NEXO bug (do it here for --append)
    if data_row.in_row[2] == "NEXONEXO":
        data_row.in_row[2] = "NEXO"

    in_row = data_row.in_row

    # outcome, detail =  [v.trim() for v in in_row[4].split('/')]
    # if re.match('(i)reject', outcome) and not config.args.unconfirmed:

    if re.match('reject', in_row[4], re.I) and not config.args.unconfirmed:
        sys.stderr.write("%srow[%s] %s\n" % (
            Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))
        sys.stderr.write("%sWARNING%s Skipping unconfirmed transaction, "
                         "use the [-uc] option to include it\n" % (
                             Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW))
        return

    data_row.timestamp = DataParser.parse_timestamp(in_row[6], tz='Europe/Amsterdam')

    if in_row[1] in ("Deposit", "ExchangeDepositedOn"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[2],
                                                 wallet=WALLET)

    elif in_row[1] == "Bonus":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[2],
                                                 wallet=WALLET)

    elif in_row[1] == "Interest":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INTEREST,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[2],
                                                 wallet=WALLET)

    elif in_row[1] in ("Withdrawal", "WithdrawExchanged"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[3])),
                                                 sell_asset=in_row[2],
                                                 wallet=WALLET)

    elif re.match('exchange|trade', in_row[1], re.I):
        sys.stderr.write("%srow[%s] %s\n" % (
            Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))
        sys.stderr.write("%sWARNING%s Skipping Exchange transaction due to Nexo bug (you can do it manually or ask Nexo to properly output all needed data)\n" % (
                             Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW))

    else:
        raise UnexpectedTypeError(1, parser.in_header[1], in_row[1])

DataParser(DataParser.TYPE_EXCHANGE,
           "Nexo",
           ['Transaction', 'Type', 'Currency', 'Amount', 'Details',
           'Outstanding Loan', 'Date / Time'],
           worksheet_name="Nexo",
           row_handler=parse_nexo)
