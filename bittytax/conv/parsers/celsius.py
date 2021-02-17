# -*- coding: utf-8 -*-
# (c) aleqx on Github

import sys
from decimal import Decimal

from colorama import Fore, Back

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

# [0] Internal id
# [1] Date and time
# [2] Transaction type
# [3] Coin type
# [4] Coin amount
# [5] USD Value
# [6] Original Interest Coin
# [7] Interest Amount In Original Coin
# [8] Confirmed

WALLET = "Celsius"

def parse_celsius(row, parser, _filename):
    r = row.in_row

    if r[8] != "Yes" and not config.args.unconfirmed:
        sys.stderr.write("%srow[%s] %s\n" % (
            Fore.YELLOW, parser.in_header_row_num + row.line_num, row))
        sys.stderr.write("%sWARNING%s Skipping unconfirmed transaction, "
                         "use the [-uc] option to include it\n" % (
                             Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW))
        return

    row.timestamp = DataParser.parse_timestamp(r[1])

    if r[2] in ('interest'):
        row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INTEREST,
                                            row.timestamp,
                                            buy_quantity=r[4],
                                            buy_asset=r[3],
                                            wallet=WALLET)

    elif r[2] in ('promo_code_reward', 'referred_award', 'referrer_award', 'bonus_token'):
        row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                            row.timestamp,
                                            buy_quantity=r[4],
                                            buy_asset=r[3],
                                            wallet=WALLET)

    elif r[2] in ('deposit', 'inbound_transfer'):
        row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                            row.timestamp,
                                            buy_quantity=r[4],
                                            buy_asset=r[3],
                                            wallet=WALLET)

    elif r[2] in ('withdrawal', 'outbound_transfer'):
        row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                            row.timestamp,
                                            sell_quantity=r[4],
                                            sell_asset=r[3],
                                            wallet=WALLET)
    else:
        raise UnexpectedTypeError(2, parser.in_header[2], r[2])


DataParser(DataParser.TYPE_WALLET,
           WALLET,
           ['Internal id', 'Date and time', 'Transaction type', 'Coin type',
            'Coin amount', 'USD Value', 'Original Interest Coin',
            'Interest Amount In Original Coin', 'Confirmed'],
           worksheet_name=WALLET,
           row_handler=parse_celsius)
