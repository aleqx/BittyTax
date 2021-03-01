# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019
# (c) aleqx on github

from decimal import Decimal

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnknownCryptoassetError

WALLET = "Electrum"

def parse_electrum(data_row, _parser, _filename):
    in_row = data_row.in_row
    txhash = in_row[0]
    label = in_row[1]
    # note = txhash + ', ' + label
    note = label
    timestamp = in_row[-1]
    wallet = config.args.wallet if config.args.wallet else WALLET
    if len(in_row) == 5:
        value = in_row[3]
    elif len(in_row) == 8:
        value = in_row[3]
    else:
        value = in_row[2]

    data_row.timestamp = DataParser.parse_timestamp(timestamp, tz='Europe/London')

    if not config.args.cryptoasset:
        raise UnknownCryptoassetError

    if Decimal(in_row[3]) > 0:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=value,
                                                 buy_asset=config.args.cryptoasset,
                                                 wallet=wallet,
                                                 note=note)
    else:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(value)),
                                                 sell_asset=config.args.cryptoasset,
                                                 wallet=wallet,
                                                 note=note)

DataParser(DataParser.TYPE_WALLET,
           WALLET,
           ['transaction_hash', 'label', 'value', 'timestamp'],
           worksheet_name=WALLET,
           row_handler=parse_electrum)

DataParser(DataParser.TYPE_WALLET,
           WALLET,
           ['transaction_hash', 'label', 'confirmations', 'value', 'timestamp'],
           worksheet_name=WALLET,
           row_handler=parse_electrum)

DataParser(DataParser.TYPE_WALLET,
           WALLET,
           ['transaction_hash', 'label', 'confirmations', 'value', 'fiat_value', 'fee', 'fiat_fee', 'timestamp'],
           worksheet_name=WALLET,
           row_handler=parse_electrum)
