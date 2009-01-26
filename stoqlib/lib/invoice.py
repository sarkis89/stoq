# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2007 Async Open Source <http://www.async.com.br>
## All rights reserved
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU Lesser General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Lesser General Public License for more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
## USA.
##
## Author(s):   Johan Dahlin             <jdahlin@async.com.br>
##
"""Invoice generation"""

import array
import datetime
from decimal import Decimal

from stoqdrivers.enum import TaxType
from stoqdrivers.escp import EscPPrinter

from stoqlib.domain.interfaces import ICompany, IIndividual
from stoqlib.lib.message import warning
from stoqlib.lib.parameters import sysparam
from stoqlib.lib.translation import stoqlib_gettext as _


def splititers(iterator, size):
    while iterator:
        yield iterator[:size]
        iterator = iterator[size:]


class InvoicePage(object):
    """This represent a page part of an invoice"""
    def __init__(self, width, height):
        """
        Create a new InvoicePage object.
        @param width: the width of the page
        @param height: the height of the page
        """
        self._data = []

        for lines in range(height):
            self._data.append(
                array.array('c', (' ' * width) + '\n'))
        self.width = width
        self.height = height

    def __iter__(self):
        return iter(self._data)

    def _put(self, x, y, width, data):
        if type(data) != str:
            raise AssertionError(type(data))
        output = array.array('c', data.upper())
        if y > len(self._data):
            raise ValueError(
                "maximum invoice layout is %d, got %d" % (
                self.height, y))

        row = self._data[y]
        row[x:x+width] = output[:width]

    def _add_boolean(self, x, y, width, data):
        if data:
            data = 'X'
        else:
            data = ' '
        self._put(x, y, width, data)

    def _add_integer(self, x, y, width, data):
        if data is None:
            data = ''
        else:
            data = '%*.2f' % (int(width), data)
        self._put(x, y, width, data)

    def _add_decimal(self, x, y, width, data):
        if data is None:
            data = ''
        else:
            data = '%*.2f' % (int(width), float(data))
        self._put(x, y, width, data)

    def _add_string(self, x, y, width, data):
        if type(data) == unicode:
            data = str(data)
        if data is None:
            data = ''
        else:
            data = '%-*s' % (int(width), data)
        self._put(x, y, width, data)

    def _add_list(self, data_type, x, y, width, height, data):
        for y_offset, line in enumerate(data):
            self.add(data_type[0], x, y + y_offset,
                     width, height, line)

    def add(self, data_type, x, y, width, height, data):
        """
        Adds a new field to the page
        @param data_type: data type of the field
        @param x: x position of the left side of the field
        @param y: y position of the upper side of the field
        @param width: width of the field
        @param height: height of the field
        @param data: data to be printed at the field. This is dependent of
          the data type
        """
        if data_type == bool:
            self._add_boolean(x, y, width, data)
        elif data_type == str:
            self._add_string(x, y, width, data)
        elif data_type == Decimal:
            self._add_decimal(x, y, width, data)
        elif data_type == int:
            self._add_integer(x, y, width, data)
        elif type(data_type) == list:
            self._add_list(data_type, x, y, width, height, data)
        else:
            raise AssertionError(
                "unsupported field type: %s" % (data_type,))


class _Invoice(object):
    def __init__(self, layout):
        self.layout = layout
        self.header_fields = []
        self.list_fields = []
        self.footer_fields = []

        self._arrange_fields()

    def _arrange_fields(self):
        """Arrange all the fields.
        We have three field types internally, headers, list and footers.
        The header iterms should appear on all pages
        The list items should be split up and separated by page
        Footer items should only appear on the last page

        List items are items are invoice fields which has a list type
        All items which has are located above a list item is a header item
        and all item which are located belove is a footer item.
        """

        # First pass, figure out upper and lower bounds of the list area,
        # eg the area which the list items cover.

        top = self.layout.height
        bottom = 0
        for field in self.layout.fields:
            invoice_field_class = get_invoice_field_by_name(field.field_name)
            if not isinstance(invoice_field_class.field_type, list):
                continue
            if field.y < top:
                top = field.y
            if (field.y + field.height) > bottom:
                bottom = field.y + field.height

        # Now when we know the interval of all the list items,
        # Just arrange the items by their relative position to the
        # list area:
        #   above area  -> header
        #   below area  -> footer
        #   inside arae -> list

        for field in self.layout.fields:
            if field.y + field.height < top:
                self.header_fields.append(field)
            elif field.y > bottom:
                self.footer_fields.append(field)
            else:
                self.list_fields.append(field)

    def _fetch_data_by_field(self, field):
        invoice_field_class = get_invoice_field_by_name(field.field_name)
        if invoice_field_class is None:
            print 'WARNING: Could not find field %s' % (field.field_name,)
            return
        invoice_field = invoice_field_class(self)
        return invoice_field.fetch(), invoice_field.field_type

    def _add_field(self, page, field):
        data, field_type = self._fetch_data_by_field(field)

        page.add(field_type,
                 field.x, field.y,
                 field.width, field.height,
                 data)

    def _fetch_list_fields(self):
        """Fetch the list field data and seperate/sort it by page.
        The dictionary returned is structured like this::
          - key: page number
          - value: field, field_type, lines for the page
            - field comes from the database
            - field_type is the type of the field
            - lines is all the lines which should be printed on
              the current page
        @returns: a dictionary
        """

        # Fetch the data from all list fields
        list_fields = []
        for field in self.list_fields:
            data, field_type = self._fetch_data_by_field(field)
            list_fields.append((field, field_type, list(data)))

        # Split up the data by page
        page_list_fields = {}
        for field, field_type, data in list_fields:
            line_data = splititers(data, field.height)
            for n, lines in enumerate(line_data):
                if not n in page_list_fields:
                    page_list_fields[n] = []
                page_list_fields[n].append((field, field_type, lines))

        return page_list_fields

    def generate_pages(self):
        """Formats the data from the sale according to the fields specified
        in the layout
        @returns: pages printed
        @rtype: a list of pages
        """

        list_field_data = self._fetch_list_fields()

        pages = []
        for page_no in sorted(list_field_data):
            list_fields = list_field_data[page_no]

            page = InvoicePage(self.layout.width, self.layout.height)

            # Header fields
            for field in self.header_fields:
                self._add_field(page, field)

            # List fields
            for field, field_type, lines in list_fields:
                page.add(field_type,
                         field.x, field.y,
                         field.width, field.height,
                         lines)
            pages.append(page)

        # Footer fields
        if pages:
            last_page = pages[-1]
            for field in self.footer_fields:
                self._add_field(last_page, field)

        return pages

    def send_to_printer(self, device):
        """Send the printer invoice to the printer
        @param device: device name of the printer
        @type device: string
        """
        try:
            printer = EscPPrinter(device)
        except IOError, e:
            warning(str(e))
            return
        for page in self.generate_pages():
            for line in page:
                printer.send(line.tostring())
            printer.form_feed()
        printer.done()


class SaleInvoice(_Invoice):
    def __init__(self, sale, layout):
        """Creates a new sale invoice
        @param sale: sale to print an invoice for
        @param layout: the invoice layout to use
        """
        _Invoice.__init__(self, layout)
        self.sale = sale
        self.type = _('Sale')
        self.today = datetime.datetime.today()


class PurchaseInvoice(_Invoice):
    def __init__(self, purchase, layout):
        _Invoice.__init__(self, layout)
        self.purchase = purchase
        self.type = _('Purchase')
        self.today = datetime.datetime.today()


class InvoiceFieldDescription(object):
    field_type = str
    height = 1
    description = ''
    name = None
    length = -1

    def __init__(self, invoice):
        self.invoice = invoice
        self.sale = invoice.sale
        self.conn = self.sale.get_connection()

    @classmethod
    def get_description(self):
        return self.description or self.name

invoice_fields = {}

def _add_invoice_field(field):
    global invoice_fields
    invoice_fields[field.name] = field

def get_invoice_field_by_name(field_name):
    global invoice_fields
    return invoice_fields.get(field_name)

def get_invoice_fields():
    global invoice_fields
    return invoice_fields.values()


class F(InvoiceFieldDescription):
    name = "COMPANY_DOCUMENT"
    description = _("Company document number")
    length =  4
    def fetch(self):
        return ICompany(self.sale.branch).cnpj

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    field_type = bool
    name = "OUTGOING_INVOICE"
    description = _("Outgoing invoice")
    length =  1
    def fetch(self):
        return isinstance(self.invoice, SaleInvoice)

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    field_type = bool
    name = "INCOMING_INVOICE"
    description = _("Incoming invoice")
    length =  1
    def fetch(self):
        return isinstance(self.invoice, PurchaseInvoice)

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "CLIENT_NAME"
    description = _('Client name')
    length =  35
    def fetch(self):
        return self.sale.client.person.name

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "CLIENT_ADDRESS"
    description = _('Client Address')
    length =  34
    def fetch(self):
        return self.sale.client.person.address.get_address_string()

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "CLIENT_DOCUMENT"
    description = _("Client's document number")
    length =  14
    def fetch(self):
        individual = IIndividual(self.sale.client, None)
        if individual is not None:
            return individual.cpf

        company = ICompany(self.sale.client, None)
        if company is not None:
            return company.cnpj

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "CLIENT_DISTRICT"
    description = _("Client's district")
    length =  15
    def fetch(self):
        return self.sale.client.person.address.district

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "CLIENT_POSTAL_CODE"
    description = _("Client's postal code")
    length =  8
    def fetch(self):
        return self.sale.client.person.address.postal_code

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "CLIENT_CITY"
    description = _("Client's city")
    length =  34
    def fetch(self):
        return self.sale.client.person.address.get_city()

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "CLIENT_PHONE"
    description = _('Client Phone number')
    length =  12
    def fetch(self):
        return self.sale.client.person.phone_number

_add_invoice_field(F)

class F(InvoiceFieldDescription):
    name = "CLIENT_FAX"
    description = _('Client Fax number')
    length =  12
    def fetch(self):
        return self.sale.client.person.fax_number

_add_invoice_field(F)

class F(InvoiceFieldDescription):
    name = "CLIENT_PHONE_FAX"
    description = _('Client Phone/Fax number')
    length =  12
    def fetch(self):
        return '%s / %s' % (
            self.sale.client.person.phone_number,
            self.sale.client.person.fax_number)

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "CLIENT_STATE"
    description = _('Client state abbreviation')
    length =  2
    def fetch(self):
        return self.sale.client.person.address.get_state()

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "CLIENT_STATE_REGISTRY_DOCUMENT"
    description = _('Clients state registry number or document number')
    length =  14
    def fetch(self):
        company = ICompany(self.sale.client, None)
        if company is None:
            return ''

        return company.state_registry

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "ORDER_EMISSION_DATE"
    description = _('Emission date')
    length =  10
    def fetch(self):
        return str(self.invoice.today.date())

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "ORDER_CREATION_DATE"
    description = _('Creation date')
    length =  10
    def fetch(self):
        return str(self.invoice.today.date())

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "ORDER_CREATION_TIME"
    description = _('Creation time')
    length =  8
    def fetch(self):
        return str(self.invoice.today.strftime('%H:%S'))

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "PAYMENT_NUMBERS"
    description = _('Number of payments')
    length =  4
    def fetch(self):
        return str(self.sale.payments.count())

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "PAYMENT_DUE_DATES"
    description = _('Payment due dates')
    length =  1
    def fetch(self):
        dates = [str(p.due_date.date()) for p in self.sale.payments]
        return ', '.join(dates)

_add_invoice_field(F)

class F(InvoiceFieldDescription):
    name = "PAYMENT_VALUES"
    description = _('Payment values')
    length =  1
    def fetch(self):
        dates = [str(p.value) for p in self.sale.payments]
        return ', '.join(dates)

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "BASE_DE_CALCULO_ICMS"
    length =  1
    field_type = Decimal
    def fetch(self):
        total = Decimal(0)
        for sale_item in self.sale.products:
            tax = sale_item.sellable.get_tax_constant()
            if not tax or not tax.tax_value:
                continue
            total += sale_item.get_total()
        return total

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "VALOR_ICMS"
    length =  1
    field_type = Decimal
    def fetch(self):
        total = Decimal(0)
        for sale_item in self.sale.products:
            tax = sale_item.sellable.get_tax_constant()
            if tax and tax.tax_value:
                total += sale_item.get_total() * (tax.tax_value / 100)
        return total

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "BASE_DE_CALCULO_ICMS_SUBST"
    length =  1
    field_type = Decimal
    def fetch(self):
        total = Decimal(0)
        for sale_item in self.sale.products:
            tax = sale_item.sellable.get_tax_constant()
            if tax.tax_type == TaxType.SUBSTITUTION:
                total += sale_item.get_total()
        return total

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "VALOR_ICMS_SUBST"
    length =  1
    field_type = Decimal
    def fetch(self):
        total = Decimal(0)
        tax_value = sysparam(self.conn).SUBSTITUTION_TAX
        for sale_item in self.sale.products:
            tax = sale_item.sellable.get_tax_constant()
            if tax.tax_type == TaxType.SUBSTITUTION:
                total += sale_item.get_total() * (Decimal(tax_value) / 100)
        return total

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "VALOR_TOTAL_PRODUTOS"
    length =  1
    field_type = Decimal
    def fetch(self):
        return self.sale.get_sale_subtotal()

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "VALOR_FRETE"
    length =  1
    def fetch(self):
        return 0

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "VALOR_SEGURO"
    length =  1
    def fetch(self):
        return 0

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "VALOR_DESPESAS"
    length =  1
    def fetch(self):
        return 0

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "VALOR_IPI"
    length =  1
    def fetch(self):
        return 0

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "VALOR_TOTAL_NOTA"
    length =  1
    field_type = Decimal
    def fetch(self):
        return self.sale.get_sale_subtotal()

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "ADDITIONAL_SALE_NOTES"
    lenght = 1
    def fetch(self):
        return ''

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "SALE_NUMBER"
    length =  1
    def fetch(self):
        return self.sale.get_order_number_str()

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "SALESPERSON_NAME"
    length =  1
    def fetch(self):
        return self.sale.get_salesperson_name()

_add_invoice_field(F)

class F(InvoiceFieldDescription):
    name = "PRODUCT_ITEM_COUNTER"
    description = _('Product item counter')
    length =  3
    field_type = [str]
    def fetch(self):
        for i in range(self.sale.products.count()):
            yield '%03d' % (i+1,)

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "PRODUCT_ITEM_CODE_DESCRIPTION"
    description = _('Product item code / description')
    length =  35
    field_type = [str]

    def fetch(self):
        for sale_item in self.sale.products:
            yield '%014d / %s' % (
                sale_item.sellable.get_code(),
                sale_item.get_description())

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "PRODUCT_ITEM_CODE_SITUATION"
    description = _('Product item situation')
    length =  1
    field_type = [str]

    def fetch(self):
        for sale_item in self.sale.products:
            yield 'N'

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "PRODUCT_ITEM_CODE_UNIT"
    description = _('Product item unit')
    length =  2
    field_type = [str]

    def fetch(self):
        for sale_item in self.sale.products:
            yield sale_item.sellable.get_unit_description()

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "PRODUCT_ITEM_QUANTITY"
    description = _('Product item quantity')
    length =  5
    field_type = [Decimal]

    def fetch(self):
        for sale_item in self.sale.products:
            yield sale_item.quantity

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "PRODUCT_ITEM_PRICE"
    description = _('Product item price')
    length =  5
    field_type = [Decimal]

    def fetch(self):
        for sale_item in self.sale.products:
            yield sale_item.price

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "PRODUCT_ITEM_TOTAL"
    description = _('Product item total (price * quantity)')
    length =  7
    field_type = [Decimal]

    def fetch(self):
        for sale_item in self.sale.products:
            yield sale_item.get_total()

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "PRODUCT_ITEM_TAX"
    description = _('Product item tax')
    length =  2
    field_type = [int]

    def fetch(self):
        for sale_item in self.sale.products:
            tax = sale_item.sellable.get_tax_constant()
            if tax and tax.tax_value:
                value = int(tax.tax_value)
            else:
                value = None
            yield value

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "INVOICE_TYPE"
    description = _("Invoice Type")
    length = 10

    def fetch(self):
        return self.invoice.type

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "CFOP"
    length = 4
    def fetch(self):
        if self.sale.cfop:
            return self.sale.cfop.code

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "STATE_REGISTRY"
    description = _("State registry number")
    length = 14
    def fetch(self):
        return ICompany(self.sale.branch).state_registry

_add_invoice_field(F)


class F(InvoiceFieldDescription):
    name = "INSCR_ESTADUAL_SUBSTITUTO_TRIB"
    length = 4
    def fetch(self):
        return ''
_add_invoice_field(F)
