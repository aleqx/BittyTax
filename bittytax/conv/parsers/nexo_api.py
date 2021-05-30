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

# debit
# currency_pseudonym
# credit
# currency_short_name
# fee
# usd_value
# type_id
# time_formated
# status
# txid
# crypto_wallet_address

WALLET = "Nexo-API"

def parse_nexo(data_row, parser, _filename):
    global WALLET

    if config.args.wallet:
        WALLET = config.args.wallet

    # fix NEXO bug (do it here for --append)
    if data_row.in_row[1] == "NEXONEXO":
        data_row.in_row[1] = "NEXO"
    if data_row.in_row[3] == "NEXONEXO":
        data_row.in_row[3] = "NEXO"

    in_row = data_row.in_row

    if re.match('reject', in_row[8], re.I) and not config.args.unconfirmed:
        sys.stderr.write("%srow[%s] %s\n" % (
            Fore.YELLOW, parser.in_header_row_num + data_row.line_num, data_row))
        sys.stderr.write("%sWARNING%s Skipping unconfirmed transaction, "
                         "use the [-uc] option to include it\n" % (
                             Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW))
        return

    data_row.timestamp = DataParser.parse_timestamp(in_row[7], tz='GMT+1')

    if in_row[6] in ("Deposit", "ExchangeDepositedOn"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(in_row[0]),
                                                 buy_asset=in_row[1],
                                                 wallet=WALLET)

    elif in_row[6] == "Bonus":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                 data_row.timestamp,
                                                 buy_quantity=Decimal(in_row[0]),
                                                 buy_asset=in_row[1],
                                                 wallet=WALLET)

    elif in_row[6] in ("Interest", "FixedTermInterest", "InterestAdditional"):
        if Decimal(in_row[0]) > 0:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INTEREST,
                                                     data_row.timestamp,
                                                     buy_quantity=Decimal(in_row[0]),
                                                     buy_asset=in_row[1],
                                                     wallet=WALLET)
        else:  # Interest on loan, ignore as it's just informational, not actually paid
            return

    elif in_row[6] in ("Withdrawal", "WithdrawExchanged"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[2])),
                                                 sell_asset=in_row[3],
                                                 fee_quantity=in_row[4],
                                                 fee_asset=in_row[3],
                                                 wallet=WALLET)

    elif in_row[6] in ("Liquidation"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_SPEND,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[2])),
                                                 sell_asset=in_row[3],
                                                 fee_quantity=in_row[4],
                                                 fee_asset=in_row[3],
                                                 note="Loan repayment",
                                                 wallet=WALLET)

    # elif re.match('exchange|trade', in_row[6], re.I):  # using regexp for future proofing
    elif in_row[6] == "ExchangeSell":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[2])),
                                                 sell_asset=in_row[3],
                                                 buy_quantity=in_row[0],
                                                 buy_asset=in_row[1],
                                                 wallet=WALLET)

    # ignore these, they are Nexo internals or not disposals
    # Note: "Repayment" is also internal, it's "Liquidation" that is the actual loan repayment transaction
    elif in_row[6] in ("DepositToExchange", "ExchangeToWithdraw", "TransferIn",
                       "TransferOut", "WithdrawalCredit", "UnlockingTermDeposit",
                       "LockingTermDeposit", "Repayment"):
        return

    else:
        raise UnexpectedTypeError(6, parser.in_header[6], in_row[6])

DataParser(DataParser.TYPE_EXCHANGE,
           WALLET,
           ['credit', 'currency_pseudonym', 'debit', 'currency_short_name',
            'fee', 'usd_value', 'type_id', 'time_formated', 'status',
            'txid', 'crypto_wallet_address'],
           worksheet_name=WALLET,
           row_handler=parse_nexo)
