# -*- coding: utf-8 -*-
# Cryptocurrency tax calculator for UK tax rules
# (c) Nano Nano Ltd 2019

import argparse
import io
import sys
import codecs
import platform
import re

import colorama
from colorama import Fore, Back
import xlrd
import glob

from .version import __version__
from .config import config
from .import_records import ImportRecords
from .export_records import ExportRecords
from .transactions import TransactionHistory
from .record import TransactionRecord
from .audit import AuditRecords
from .price.valueasset import ValueAsset
from .price.exceptions import DataSourceError
from .tax import TaxCalculator, CalculateCapitalGains as CCG
from .report import ReportLog, ReportPdf
from .exceptions import ImportFailureError

if sys.stdout.encoding != 'UTF-8':
    if sys.version_info[:2] >= (3, 7):
        sys.stdout.reconfigure(encoding='utf-8')
    elif sys.version_info[:2] >= (3, 1):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    else:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout)

def main():
    colorama.init()
    parser = argparse.ArgumentParser()
    parser.add_argument('filename',
                        type=str,
                        nargs='*',
                        help="filename(s) of transaction records, "
                             "or can read CSV data from standard input")
    parser.add_argument('-v',
                        '--version',
                        action='version',
                        version='%s v%s' % (parser.prog, __version__))
    parser.add_argument('-d',
                        '--debug',
                        action='store_true',
                        help="enable debug logging")
    parser.add_argument('-ty',
                        '--taxyear',
                        type=validate_year,
                        help="tax year must be in the range (%s-%s)" % (
                            min(CCG.CG_DATA_INDIVIDUALS),
                            max(CCG.CG_DATA_INDIVIDUALS)))
    parser.add_argument('--skipint',
                        dest='skip_integrity',
                        action='store_true',
                        help="skip integrity check")
    parser.add_argument('--summary',
                        action='store_true',
                        help="only output the capital gains summary in the tax report")
    parser.add_argument('-o',
                        dest='output_filename',
                        type=str,
                        help="specify the output filename for the tax report")
    parser.add_argument('--nopdf',
                        action='store_true',
                        help="don't output PDF report, output report to terminal only")
    parser.add_argument('--noprice', '--noprices',
                        action='store_true',
                        help="don't output price data in Appendix")
    parser.add_argument('--notx', '--notxs',
                        action='store_true',
                        help="don't output individual transactions")
    parser.add_argument('--nowallet', '--nowallets',
                        dest='ignore_wallet_names',
                        action='store_true',
                        help="ignore wallet names and assume a single global wallet")
    parser.add_argument('--yearstart',
                        type=validate_start_of_year,
                        help="tax year start date as DD-MM (default %02d-%02d)" % (
                            config.tax_year_start_day, config.tax_year_start_month))
    parser.add_argument('--bnb',
                        type=validate_bnb,
                        help="bed and breakfast duration must be at least 1 (default %d)" % (
                            config.bed_and_breakfast_days))
    parser.add_argument('--transfers',
                        dest="transfers_include",
                        type=int,
                        default=int(config.transfers_include),
                        help="1=consider transfers, 0=ignore transfers from tax calculation only, -1=ignore transfers entirely")
    parser.add_argument('--export',
                        action='store_true',
                        help="export your transaction records populated with price data")
    parser.add_argument('--noauditwarning',
                        action='store_true',
                        help="ignore audit warnings about negative balances")
    parser.add_argument('--allowgiftdupes',
                        action='store_true',
                        help="ignore duplicates between gifts and deposits/withdrawals")
    parser.add_argument('--filterinclude',
                        dest="include_filters",
                        type=validate_field_filter,
                        default=[],
                        help="syntax FIELD=REGEX[,...] (case insensitive), include only rows whose FIELD value matches, e.g. Note=^missus; commas in FIELD or REGEX must be escaped, i.e. \\,.")
    parser.add_argument('--filterexclude',
                        dest="exclude_filters",
                        type=validate_field_filter,
                        default=[],
                        help="same as --include, but instead exclude rows whose FIELD value matches (can be used in conjunction with --include)")
    parser.add_argument('--joint',
                        dest="joint",
                        type=validate_joint,
                        # default=[],
                        help="joint account treatment. Syntax --joint COL where COL is the name of a column which holds weights for one of the members of the joint account. The weight is considered as a percentage, i.e. it must be less or equal to 1.")

    config.args = parser.parse_args()
    config.args.nocache = False
    config.transfers_include = config.args.transfers_include > 0

    if config.args.debug:
        print("%s%s v%s" % (Fore.YELLOW, parser.prog, __version__))
        print("%spython: v%s" % (Fore.GREEN, platform.python_version()))
        print("%ssystem: %s, release: %s" % (Fore.GREEN, platform.system(), platform.release()))
        config.output_config()

    transaction_records = do_import(config.args.filename, parser)

    if not config.args.allowgiftdupes:
        transaction_records = remove_gift_dupes(transaction_records)

    if config.args.export:
        do_export(transaction_records)
        parser.exit()

    audit = AuditRecords(transaction_records)

    try:
        tax, value_asset = do_tax(transaction_records)
        if not config.args.skip_integrity:
            int_passed = do_integrity_check(audit, tax.holdings)
            if not int_passed:
                parser.exit()

        if not config.args.summary:
            tax.process_income()

        do_each_tax_year(tax,
                         config.args.taxyear,
                         config.args.summary,
                         value_asset)

    except DataSourceError as e:
        parser.exit("%sERROR%s %s" % (
            Back.RED+Fore.BLACK, Back.RESET+Fore.RED, e))

    if config.args.nopdf:
        ReportLog(audit,
                  tax.tax_report,
                  value_asset.price_report,
                  tax.holdings_report)
    else:
        ReportPdf(parser.prog,
                  audit,
                  tax.tax_report,
                  value_asset.price_report,
                  tax.holdings_report)

def is_gift_dupe(tx1: TransactionRecord, tx2: TransactionRecord):
    return tx1.timestamp == tx2.timestamp and ( #tx1.wallet == tx2.wallet and (
            (  # received
                (tx1.t_type in (TransactionRecord.TYPE_GIFT_RECEIVED,
                                TransactionRecord.TYPE_MINING,
                                TransactionRecord.TYPE_INTEREST,
                                TransactionRecord.TYPE_INCOME) and tx2.t_type == TransactionRecord.TYPE_DEPOSIT
                 or tx2.t_type in (TransactionRecord.TYPE_GIFT_RECEIVED,
                                   TransactionRecord.TYPE_MINING,
                                   TransactionRecord.TYPE_INTEREST,
                                   TransactionRecord.TYPE_INCOME) and tx1.t_type == TransactionRecord.TYPE_DEPOSIT)
                and tx1.buy.asset == tx2.buy.asset
                and abs(tx1.buy.quantity - tx2.buy.quantity) <= 0.00000001
            ) or (  # sent
                (tx1.t_type in (TransactionRecord.TYPE_SPEND,
                                TransactionRecord.TYPE_GIFT_SPOUSE,
                                TransactionRecord.TYPE_GIFT_SENT,
                                TransactionRecord.TYPE_CHARITY_SENT) and tx2.t_type == TransactionRecord.TYPE_WITHDRAWAL
                 or tx2.t_type in (TransactionRecord.TYPE_SPEND,
                                   TransactionRecord.TYPE_GIFT_SPOUSE,
                                   TransactionRecord.TYPE_GIFT_SENT,
                                   TransactionRecord.TYPE_CHARITY_SENT) and tx1.t_type == TransactionRecord.TYPE_WITHDRAWAL)
                and tx1.sell.asset == tx2.sell.asset
                and abs(tx1.sell.quantity - tx2.sell.quantity) <= 0.00000001
            )
    )

def remove_gift_dupes(txs):
    indices = []
    # check and make sure we don't remove gifts but withdrawal/deposits
    for i in range(0, len(txs)-1):
        for j in range(i+1, len(txs)):
            if txs[i].timestamp == txs[j].timestamp:  # lookahead as long as timestamps are the same
                if is_gift_dupe(txs[i], txs[j]):
                    indices.append(i if txs[i].t_type in (TransactionRecord.TYPE_WITHDRAWAL, TransactionRecord.TYPE_DEPOSIT) else j)
            else:
                break
    indices = list(set(indices))  # make unique
    if len(indices) > 0:
        indices.sort(reverse=True)
        for i in indices:
            print("%sWARNING%s income/spend/gift duplicate removed: %s" % (Back.YELLOW + Fore.BLACK, Back.RESET + Fore.YELLOW, txs[i].to_csv()))
            del txs[i]
    return txs

def validate_joint(value):
    return {
        "field":      value,
        "column":     0,
        "findcolumn": lambda header, field: field if isinstance(field, int) else [e.lower() for e in header].index(field.lower())
    }

def validate_field_filter(value):
    try:
        filters = []
        for filt in re.split(r'(?<!\\),\s*', value):
            field, restr = filt.replace('\\,', ',').split('=', 1)
            filters.append({
                'field': int(field) if re.match(r'\d+', field) else field.lower(),
                'column': -1,
                're': re.compile(restr, re.I),
                'findcolumn': lambda header, field: field if isinstance(field, int) else [e.lower() for e in header].index(field)
            })
        return filters
    except ValueError:
        raise argparse.ArgumentTypeError("malformed FIELD=REGEXP[,...] string: %s" % value)

def validate_year(value):
    year = int(value)
    if year not in CCG.CG_DATA_INDIVIDUALS:
        raise argparse.ArgumentTypeError("tax year %d is not supported, "
                                         "must be in the range (%s-%s)" % (
            year,
            min(CCG.CG_DATA_INDIVIDUALS),
            max(CCG.CG_DATA_INDIVIDUALS)))

    return year

def validate_start_of_year(value):
    day, month = map(int, value.split('-', 2))
    month_days = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]  # 29 Feb will never be a tax year start date
    if month > 12 or month < 1 or day < 1 or day > month_days[month]:
        raise argparse.ArgumentTypeError("tax year start date as DD-MM (default %d-%d)" % (
            config.tax_year_start_day, config.tax_year_start_month))
    config.tax_year_start_day = day
    config.tax_year_start_month = month

def validate_bnb(value):
    value = int(value)
    if value < 1:
        raise argparse.ArgumentTypeError("bed and breakfast duration must be at least 1 (default %d)" % (
                            config.bed_and_breakfast_days))
    config.bed_and_breakfast_days = value

def do_import(filenames, parser):
    real_filenames = []
    for f in filenames:
        if re.search(r'\{.*?\}|\[.*?\]|\*|\?', f) and isinstance(glob.glob(f), list):
            real_filenames = real_filenames + glob.glob(f)
        else:
            real_filenames.append(f)

    import_records = ImportRecords()
    for filename in real_filenames:
        try:
            if filename:
                if filename[0] == '~':
                    print("%sWARNING%s Skipping file: %s" % (Back.YELLOW + Fore.BLACK, Back.RESET + Fore.YELLOW, filename))
                    continue
                try:
                    import_records.import_excel(filename)
                except xlrd.XLRDError:
                    with io.open(filename, newline='', encoding='utf-8') as csv_file:
                        import_records.import_csv(csv_file)
            else:
                if sys.version_info[0] < 3:
                    import_records.import_csv(codecs.getreader('utf-8')(sys.stdin))
                else:
                    import_records.import_csv(sys.stdin)

            print("%simport %s (success=%s, failure=%s)" % (
                Fore.WHITE, 'successful' if import_records.failure_cnt <= 0 else 'failure',
                import_records.success_cnt, import_records.failure_cnt))

            if import_records.failure_cnt > 0:
                raise ImportFailureError

        except IOError:
            parser.exit("%sERROR%s File could not be read: %s" % (
                Back.RED+Fore.BLACK, Back.RESET+Fore.RED, filename))
        except ImportFailureError:
            parser.exit()

    return import_records.get_records()

def do_tax(transaction_records):
    value_asset = ValueAsset()
    transaction_history = TransactionHistory(transaction_records, value_asset)

    tax = TaxCalculator(transaction_history.transactions)
    tax.pool_same_day()
    tax.match(tax.DISPOSAL_SAME_DAY)
    tax.match(tax.DISPOSAL_BED_AND_BREAKFAST)
    tax.process_section104()
    return tax, value_asset

def do_integrity_check(audit, holdings):
    int_passed = True

    if config.transfers_include:
        transfer_mismatch = transfer_mismatches(holdings)
    else:
        transfer_mismatch = False

    pools_match = audit.compare_pools(holdings)

    if not pools_match or transfer_mismatch:
        int_passed = False

    print("%sintegrity check: %s%s" % (
        Fore.CYAN, Fore.YELLOW, 'passed' if int_passed else 'failed'))

    if transfer_mismatch:
        print("%sWARNING%s Integrity check failed: disposal(s) detected during transfer, "
              "turn on logging [-d] to see transactions" % (
                  Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW))
    elif not pools_match:
        if not config.transfers_include:
            print("%sWARNING%s Integrity check failed: audit does not match section 104 pools, "
                  "please check Withdrawals and Deposits for missing fees" % (
                      Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW))
        else:
            print("%sERROR%s Integrity check failed: audit does not match section 104 pools" % (
                Back.RED+Fore.BLACK, Back.RESET+Fore.RED))
        audit.report_failures()
    return int_passed

def transfer_mismatches(holdings):
    return bool([asset for asset in holdings if holdings[asset].mismatches])

def do_each_tax_year(tax, tax_year, summary, value_asset):
    if tax_year:
        print("%scalculating tax year %d/%d" % (
            Fore.CYAN, tax_year - 1, tax_year))
        tax.calculate_capital_gains(tax_year)
        if not summary:
            tax.calculate_income(tax_year)
    else:
        # Calculate for all years
        for year in sorted(tax.tax_events):
            print("%scalculating tax year %d/%d" % (
                Fore.CYAN, year - 1, year))
            if year in CCG.CG_DATA_INDIVIDUALS:
                tax.calculate_capital_gains(year)
                if not summary:
                    tax.calculate_income(year)
            else:
                print("%sWARNING%s Tax year %s is not supported" % (
                    Back.YELLOW+Fore.BLACK, Back.RESET+Fore.YELLOW, year))

        if not summary:
            tax.calculate_holdings(value_asset)

    return tax, value_asset

def do_export(transaction_records):
    value_asset = ValueAsset()
    TransactionHistory(transaction_records, value_asset)
    ExportRecords(transaction_records).write_csv()

if __name__ == "__main__":
    main()
