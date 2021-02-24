# -*- coding: utf-8 -*-
# (c) Nano Nano Ltd 2020
# (c) aleqx on github 2021

# TODO: (aleqx)
#  - The types "dynamic_coin_swap_{credited,debited}" seem to be duplicates
#    of "crypto_wallet_swap_{credited,debited}", hence just ignore.
#  - The type "dynamic_coin_swap_bonus_exchange_deposit" seems redundant as it should
#    be present on the exchange records, not the app's, hence ignore.
#  - The types "lockup_swap_credited", "interest_swap_credited" do _not_ seem redundant.
#  Revisit if any evidence is presented to the contrary of any of the above.

from decimal import Decimal
from functools import reduce

from ...config import config
from ..out_record import TransactionOutRecord
from ..dataparser import DataParser
from ..exceptions import DataParserError, UnexpectedTypeError

WALLET = "Crypto.com"

def parse_crypto_com_all(data_rows, parser, _filename):
    # order chronologically
    data_rows.sort(key=lambda row: row.in_row[0])
    debited_rows = []
    credited_row = {}
    # Swaps and dust conversions span multiple "debited" and "credited" rows;
    # there are multiple "debited" rows in a dust conversion; the order of
    # debited/credited can be arbitrary; hence we gobble till we hit non-swap rows.
    for data_row in data_rows:
        try:
            in_row = data_row.in_row
            data_row.timestamp = DataParser.parse_timestamp(in_row[0])
            if in_row[9] in ("dust_conversion_credited", "crypto_wallet_swap_credited",
                             "lockup_swap_credited", "interest_swap_credited"):
                credited_row = data_row
                continue
            elif in_row[9] in ("dust_conversion_debited", "crypto_wallet_swap_debited",
                               "lockup_swap_debited", "interest_swap_debited"):
                debited_rows.append(data_row)
                continue
            elif len(debited_rows) == 0 or not credited_row:
                parse_crypto_com(data_row, parser, _filename)
            else:  # hit a non-swap row after a sequence of swap rows
                total_debited_native = reduce(lambda x, y: x + y, [Decimal(data_row.in_row[7]) for data_row in debited_rows])
                for debited_row in debited_rows:
                    debited_row.in_row[4] = credited_row.in_row[2]
                    debited_row.in_row[5] = str(Decimal(credited_row.in_row[3]) * Decimal(debited_row.in_row[7]) / total_debited_native) \
                        if total_debited_native > 0 else str(Decimal(credited_row.in_row[3]) / len(debited_rows))
                    debited_row.in_row[9] = debited_row.in_row[9].replace('_debited', '')  # rename type
                    parse_crypto_com(debited_row, parser, _filename)
                debited_rows = []
                credited_row = {}
                # parse the non-swap row too
                parse_crypto_com(data_row, parser, _filename)

        except DataParserError as e:
            data_row.failure = e


def parse_crypto_com(data_row, parser, _filename):
    in_row = data_row.in_row
    # data_row.timestamp = DataParser.parse_timestamp(in_row[0])
    note = in_row[1]
    # note = ''

    if in_row[9] == "crypto_transfer":
        if Decimal(in_row[3]) > 0:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                     data_row.timestamp,
                                                     buy_quantity=in_row[3],
                                                     buy_asset=in_row[2],
                                                     buy_value=get_value(in_row),
                                                     note=note,
                                                     wallet=WALLET)
        else:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_SENT,
                                                     data_row.timestamp,
                                                     sell_quantity=abs(Decimal(in_row[3])),
                                                     sell_asset=in_row[2],
                                                     sell_value=get_value(in_row),
                                                     note=note,
                                                     wallet=WALLET)
    elif in_row[9] in ("crypto_earn_interest_paid", "mco_stake_reward",
                       "crypto_earn_extra_interest_paid"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_INTEREST,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[2],
                                                 buy_value=get_value(in_row),
                                                 note=note,
                                                 wallet=WALLET)
    elif in_row[9] in ("viban_purchase", "van_purchase",
                       "crypto_viban_exchange", "crypto_exchange",
                       "dust_conversion", "crypto_wallet_swap"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[5],
                                                 buy_asset=in_row[4],
                                                 sell_quantity=abs(Decimal(in_row[3])),
                                                 sell_asset=in_row[2],
                                                 sell_value=get_value(in_row),
                                                 note=note,
                                                 wallet=WALLET)
    elif in_row[9] in ("crypto_purchase"):
        if Decimal(in_row[3]) > 0:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                     data_row.timestamp,
                                                     buy_quantity=in_row[3],
                                                     buy_asset=in_row[2],
                                                     sell_quantity=in_row[7],
                                                     sell_asset=in_row[6],
                                                     note=note,
                                                     wallet=WALLET)
        else:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_TRADE,
                                                     data_row.timestamp,
                                                     buy_quantity=abs(Decimal(in_row[7])),
                                                     buy_asset=in_row[6],
                                                     sell_quantity=abs(Decimal(in_row[3])),
                                                     sell_asset=in_row[2],
                                                     note=note,
                                                     wallet=WALLET)
    elif in_row[9] in ("referral_bonus", "referral_card_cashback", "reimbursement",
                       "gift_card_reward", "transfer_cashback", "admin_wallet_credited",
                       "referral_gift", "campaign_reward", "mobile_airtime_reward"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_RECEIVED,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[2],
                                                 buy_value=get_value(in_row),
                                                 note=note,
                                                 wallet=WALLET)

    elif in_row[9] in ("card_cashback_reverted", "reimbursement_reverted"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_GIFT_SENT,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[3])),
                                                 sell_asset=in_row[2],
                                                 sell_value=get_value(in_row),
                                                 note=note,
                                                 wallet=WALLET)
    elif in_row[9] in ("crypto_payment", "card_top_up"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_SPEND,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[3])),
                                                 sell_asset=in_row[2],
                                                 sell_value=get_value(in_row),
                                                 note=note,
                                                 wallet=WALLET)
    elif in_row[9] in ("crypto_withdrawal", "crypto_to_exchange_transfer"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                 data_row.timestamp,
                                                 sell_quantity=abs(Decimal(in_row[3])),
                                                 sell_asset=in_row[2],
                                                 sell_value=get_value(in_row),
                                                 note=note,
                                                 wallet=WALLET)
    elif in_row[9] in ("crypto_deposit", "exchange_to_crypto_transfer"):
        data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                 data_row.timestamp,
                                                 buy_quantity=in_row[3],
                                                 buy_asset=in_row[2],
                                                 buy_value=get_value(in_row),
                                                 note=note,
                                                 wallet=WALLET)
    elif in_row[9] in ("crypto_earn_program_created", "crypto_earn_program_withdrawn",
                       "lockup_lock", "lockup_upgrade",
                       "dynamic_coin_swap_credited", "dynamic_coin_swap_debited",
                       "dynamic_coin_swap_bonus_exchange_deposit",
                       "supercharger_deposit", "supercharger_withdrawal"):
        return
    elif in_row[9] == "":
        # Could be a fiat transaction
        if "Deposit" in in_row[1]:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_DEPOSIT,
                                                     data_row.timestamp,
                                                     buy_quantity=in_row[3],
                                                     buy_asset=in_row[2],
                                                     note=note,
                                                     wallet=WALLET)
        elif "Withdrawal" in in_row[1]:
            data_row.t_record = TransactionOutRecord(TransactionOutRecord.TYPE_WITHDRAWAL,
                                                     data_row.timestamp,
                                                     sell_quantity=abs(Decimal(in_row[3])),
                                                     sell_asset=in_row[2],
                                                     note=note,
                                                     wallet=WALLET)
    else:
        raise UnexpectedTypeError(9, parser.in_header[9], in_row[9])

def get_value(in_row):
    if in_row[6] == config.CCY:
        return abs(Decimal(in_row[7]))
    return None

DataParser(DataParser.TYPE_EXCHANGE,
           "Crypto.com",
           ['Timestamp (UTC)', 'Transaction Description', 'Currency', 'Amount', 'To Currency',
            'To Amount', 'Native Currency', 'Native Amount', 'Native Amount (in USD)',
            'Transaction Kind'],
           worksheet_name="Crypto.com",
           # row_handler=parse_crypto_com)
           all_handler=parse_crypto_com_all)
