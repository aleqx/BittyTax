# -*- coding: utf-8 -*-
# (c) aleqx on github

from decimal import Decimal

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "KuCoin-New"

def parse_kucoin_trades_v2(data_row, parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[8], tz='Asia/Hong_Kong')
    coin, base = in_row[1].split('-')
    base_quantity = Decimal(in_row[6])-Decimal(in_row[7])

    if in_row[5] == "BUY":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[4],
                                                 buy_asset=coin,
                                                 sell_quantity=base_quantity,
                                                 sell_asset=base,
                                                 fee_quantity=in_row[7],
                                                 fee_asset=base,
                                                 wallet=WALLET)
    elif in_row[5] == "SELL":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=base_quantity,
                                                 buy_asset=base,
                                                 sell_quantity=in_row[4],
                                                 sell_asset=coin,
                                                 fee_quantity=in_row[7],
                                                 fee_asset=base,
                                                 wallet=WALLET)
    else:
        raise UnexpectedTypeError(5, parser.in_header[5], in_row[5])

def parse_kucoin_trades_v1(data_row, parser, _filename):
    # Kucoin V1 no longer exports fee information (RIP)
    # Kucoin had a 0.1% fee before Feb 2019 for VIP0 level.
    # Use --fee 0.1 in the command line
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[6], tz='Asia/Hong_Kong')
    coin, base = in_row[1].split('-')
    fee_quantity = Decimal(in_row[5]) * Decimal(config.args.fee)
    base_quantity = Decimal(in_row[5]) - fee_quantity

    if in_row[2] == "BUY":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[4],
                                                 buy_asset=coin,
                                                 sell_quantity=base_quantity,
                                                 sell_asset=base,
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=base,
                                                 wallet=WALLET)
    elif in_row[2] == "SELL":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=base_quantity,
                                                 buy_asset=base,
                                                 sell_quantity=in_row[4],
                                                 sell_asset=coin,
                                                 fee_quantity=fee_quantity,
                                                 fee_asset=base,
                                                 wallet=WALLET)  # yes, there is no fee column, RIP
    else:
        raise UnexpectedTypeError(2, parser.in_header[2], in_row[2])

def parse_kucoin_transfers(data_row, parser, _filename):
    # Kucoin does not show withdrawal fee (RIP)
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[5], tz='Asia/Hong_Kong')

    if in_row[1] == "DEPOSIT":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[4],
                                                 buy_asset=in_row[0],
                                                 wallet=WALLET)
    elif in_row[1] == "WITHDRAW":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=in_row[4][1:],
                                                 sell_asset=in_row[0],
                                                 wallet=WALLET)  # yes, there is no fee column, RIP
    else:
        raise UnexpectedTypeError(1, parser.in_header[1], in_row[1])

DataParser(DataParser.TYPE_EXCHANGE,
           WALLET,
           ['UID', 'symbol', 'order_type', 'price', 'amount_coin', 'direction', 'funds', 'fee', 'created_at'],
           worksheet_name=WALLET,
           row_handler=parse_kucoin_trades_v2)

DataParser(DataParser.TYPE_EXCHANGE,
           WALLET,
           ['UID', 'symbol', 'direction', 'deal_price', 'amount', 'deal_value', 'created_at'],
           worksheet_name=WALLET,
           row_handler=parse_kucoin_trades_v1)

DataParser(DataParser.TYPE_EXCHANGE,
           WALLET,
           ['coin_type', 'type', 'add', 'hash', 'vol', 'created_at'],
           worksheet_name=WALLET,
           row_handler=parse_kucoin_transfers)
