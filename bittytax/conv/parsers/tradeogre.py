# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2019

from decimal import Decimal

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import UnexpectedTypeError

WALLET = "TradeOgre"
FEE_PC = 0.2  # default fee on Tradeogre in percentage is 0.2%

def parse_ogre_trades(data_row, parser, _filename):
    in_row = data_row.in_row
    data_row.timestamp = DataParser.parse_timestamp(in_row[2])
    base, coin = in_row[1].split('-')
    price = Decimal(in_row[4])
    coin_amount = Decimal(in_row[3])
    fee = Decimal(0.01 * (config.args.fee if config.args.fee > 0 else FEE_PC))
    base_amount = (coin_amount * price).quantize(Decimal('.00000001'), rounding='ROUND_DOWN')
    fee_amount = (base_amount * fee).quantize(Decimal('.00000001'), rounding='ROUND_DOWN')
    # - in Tradeogre:
    #   - sell or buy refer to the coin (2nd asset)
    #   - the fee asset is always in the base asset
    # - in Bittytax:
    #   - the sellAmount is the net amount (after fees) if the fee asset is the same as the sell asset, else the gross amount
    #   - the buy amount is always the gross amount
    if data_row.in_row[0] == "SELL":
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 sell_quantity=coin_amount,
                                                 sell_asset=coin,
                                                 buy_quantity=base_amount,
                                                 buy_asset=base,
                                                 fee_quantity=fee_amount,
                                                 fee_asset=base,
                                                 wallet=WALLET)
    else:
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 sell_quantity=base_amount,
                                                 sell_asset=base,
                                                 buy_quantity=coin_amount,
                                                 buy_asset=coin,
                                                 fee_quantity=fee_amount,
                                                 fee_asset=base,
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
           ['Type', 'Exchange', 'Date', 'Amount', 'Price'],
           worksheet_name="Ogre T",
           row_handler=parse_ogre_trades)

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
