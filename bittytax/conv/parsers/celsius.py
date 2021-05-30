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

def parse_celsius(data_row, parser, _filename):
    if config.args.wallet:
        WALLET = config.args.wallet

    in_row = data_row.in_row

    if in_row[8] != "Yes" and not config.args.unconfirmed:
        sys.stderr.write("%srow[%s] %s\n" % (
            Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))
        sys.stderr.write("%sWARNING%s Skipping unconfirmed transaction, "
                         "use the [-uc] option to include it\n" % (
                             Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW))
        return

    data_row.timestamp = DataParser.parse_timestamp(in_row[1])

    if in_row[2] in ('interest'):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INTEREST,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[4],
                                                 buy_asset=in_row[3],
                                                 wallet=WALLET)

    elif in_row[2] in ('promo_code_reward', 'referred_award', 'referrer_award', 'bonus_token'):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[4],
                                                 buy_asset=in_row[3],
                                                 wallet=WALLET)

    elif in_row[2] in ('deposit', 'inbound_transfer'):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[4],
                                                 buy_asset=in_row[3],
                                                 wallet=WALLET)

    elif in_row[2] in ('withdrawal', 'outbound_transfer'):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=in_row[4][1:],
                                                 sell_asset=in_row[3],
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(2, parser.in_header[2], in_row[2])


DataParser(DataParser.TYPE_WALLET,
           WALLET,
           ['Internal id', 'Date and time', 'Transaction type', 'Coin type',
            'Coin amount', 'USD Value', 'Original Interest Coin',
            'Interest Amount In Original Coin', 'Confirmed'],
           worksheet_name=WALLET,
           row_handler=parse_celsius)
