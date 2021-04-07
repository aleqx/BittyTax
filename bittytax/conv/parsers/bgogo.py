# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "Bgogo"

def parse_bgogo_trades(data_row, parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])
    coin, base = in_row[1].split('/')
    if data_row.in_row[2] == "Buy":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 sell_quantity=in_row[4],
                                                 sell_asset=coin,
                                                 buy_quantity=in_row[8],
                                                 buy_asset=base,
                                                 fee_quantity=in_row[5],
                                                 fee_asset=in_row[6],
                                                 wallet=WALLET)
    else:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 sell_quantity=in_row[8],
                                                 sell_asset=base,
                                                 buy_quantity=in_row[4],
                                                 buy_asset=coin,
                                                 fee_quantity=in_row[5],
                                                 fee_asset=in_row[6],
                                                 wallet=WALLET)

def parse_ogre_deposits(data_row, _parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])

    data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                             data_row.timestamp,
                                             buy_quantity=in_row[3],
                                             buy_asset=in_row[1],
                                             wallet=WALLET)

def parse_ogre_withdrawals(data_row, _parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[0])

    data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                             data_row.timestamp,
                                             sell_quantity=Decimal(in_row[3])-Decimal(in_row[4]),
                                             sell_asset=in_row[1],
                                             fee_quantity=in_row[4],
                                             fee_asset=in_row[1],
                                             wallet=WALLET)

DataParser(DataParser.TYPE_EXCHANGE,
           "TradeOgre Trades",
           ['time', 'pair', 'type', 'unitPrice', 'amount', 'fee', 'feeCoin', 'avgPrice', 'total', 'status'],
           worksheet_name="Bgogo T",
           row_handler=parse_bgogo_trades)

DataParser(DataParser.TYPE_EXCHANGE,
           "TradeOgre Deposits",
           ['Date', 'Coin', 'TXID', 'Amount'],
           worksheet_name="Ogre D",
           row_handler=parse_ogre_deposits)

DataParser(DataParser.TYPE_EXCHANGE,
           "TradeOgre Withdrawals",
           ['Date', 'Coin', 'TXID', 'Amount', 'Fee', 'Address', 'Payment ID'],
           worksheet_name="Ogre W",
           row_handler=parse_ogre_withdrawals)
