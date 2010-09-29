# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2005-2008 Async Open Source
##
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU Lesser General Public License
## as published by the Free Software Foundation; either version 2
## of the License, or (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Lesser General Public License for more details.
##
## You should have received a copy of the GNU Lesser General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., or visit: http://www.gnu.org/.
##
##
## Author(s):    Evandro Vale Miquelito     <evandro@async.com.br>
##               Henrique Romano            <henrique@async.com.br>
##
""" Parameters and system data for applications"""

from decimal import Decimal

from kiwi.argcheck import argcheck
from kiwi.log import Logger
from kiwi.python import namedAny, ClassInittableObject
from stoqdrivers.enum import TaxType

from stoqlib.database.runtime import new_transaction
from stoqlib.domain.parameter import ParameterData
from stoqlib.domain.interfaces import ISupplier, IBranch
from stoqlib.exceptions import DatabaseInconsistency
from stoqlib.lib.imageutils import ImageHelper
from stoqlib.lib.translation import stoqlib_gettext

_ = stoqlib_gettext

class DirectoryParameter(object):
    def __init__(self, path):
        self.path = path


log = Logger('stoqlib.parameters')

class ParameterDetails:
    def __init__(self, group, short_desc, long_desc):
        self.group = group
        self.short_desc = short_desc
        self.long_desc = long_desc

_parameter_info = dict(
    EDIT_CODE_PRODUCT=ParameterDetails(
     (u'Products'),
     (u'Disable edit code products'),
     (u'Disable edit code products on purchase application')),

    MAIN_COMPANY=ParameterDetails(
    _(u'General'),
    _(u'Main Company'),
    _(u'The main company which is the owner of all other branch companies')),

    CUSTOM_LOGO_FOR_REPORTS=ParameterDetails(
    _(u'General'),
    _(u'Custom logotype for reports'),
    _(u'Defines a custom logo for all the reports generated by Stoq. '
      'The recommended image dimension is 171x59 (pixels), if needed, '
      'the image will be resized. In order to use the default logotype '
      'leave this field blank')),

    DISABLE_COOKIES=ParameterDetails(
    _(u'General'),
    _(u'Disable Cookies'),
    _(u'Disable the ability to use cookies in order to automatic log in '
      'the system. If so, all the users will have to provide the password '
      'everytime they log in. Requires restart to take effect.')),

    DEFAULT_SALESPERSON_ROLE=ParameterDetails(
    _(u'Sales'),
    _(u'Default Salesperson Role'),
    _(u'Defines which of the employee roles existent in the system is the '
      'salesperson role')),

    SUGGESTED_SUPPLIER=ParameterDetails(
    _(u'Purchase'),
    _(u'Suggested Supplier'),
    _(u'The supplier suggested when we are adding a new product in the '
      'system')),

    SUGGESTED_UNIT=ParameterDetails(
    _(u'Purchase'),
    _(u'Suggested Unit'),
    _(u'The unit suggested when we are adding a new product in the '
      'system')),

    DEFAULT_BASE_CATEGORY=ParameterDetails(
    _(u'Purchase'),
    _(u'Default Base Sellable Category'),
    _(u'A default base sellable category which we always get as a '
      'suggestion when adding a new Sellable on the system')),

    ALLOW_OUTDATED_PURCHASES=ParameterDetails(
    _(u'Purchase'),
    _(u'Allow outdated purchases'),
    _(u'Allows the inclusion of purchases done previously than the '
      'current date.')),

    DEFAULT_PAYMENT_DESTINATION=ParameterDetails(
    _(u'Financial'),
    _(u'Default Payment Destination'),
    _(u'A default payment destination which will be used for all the '
      'created payments until the user change the destination of each '
      'payment method.')),

    DELIVERY_SERVICE=ParameterDetails(
    _(u'Sales'),
    _(u'Delivery Service'),
    _(u'The default delivery service in the system.')),

    USE_LOGIC_QUANTITY=ParameterDetails(
    _(u'Stock'),
    _(u'Use Logic Quantity'),
    _(u'An integer that defines if the company can work or not with '
      'logic quantities during stock operations. See StockItem '
      'documentation.')),

    # XXX This parameter is Stoq-specific. How to deal with that
    # in a better way?
    POS_FULL_SCREEN=ParameterDetails(
    _(u'Sales'),
    _(u'Show POS Application Full Screen'),
    _(u'Once this parameter is set the Point of Sale application '
      'will be showed as full screen')),

    POS_SEPARATE_CASHIER=ParameterDetails(
    _(u'Sales'),
    _(u'Exclude cashier operations in Point of Sale'),
    _(u'If you have a computer that will be a Point of Sales and have a '
      'fiscal printer connected, set this False, so the Till menu will '
      'appear on POS. If you prefer to separate the Till menu from POS '
      'set this True.')),

    ENABLE_PAULISTA_INVOICE=ParameterDetails(
    _(u'Sales'),
    _(u'Enable Paulista Invoice'),
    _(u'Once this parameter is set, we will be able to join to the '
      u'Sao Paulo state program of fiscal commitment.')),

    CITY_SUGGESTED=ParameterDetails(
    _(u'General'),
    _(u'City Suggested'),
    _(u'When adding a new address for a certain person we will always '
      'suggest this city.')),

    STATE_SUGGESTED=ParameterDetails(
    _(u'General'),
    _(u'State Suggested'),
    _(u'When adding a new address for a certain person we will always '
      'suggest this state.')),

    COUNTRY_SUGGESTED=ParameterDetails(
    _(u'General'),
    _(u'Country Suggested'),
    _(u'When adding a new address for a certain person we will always '
      'suggest this country.')),

    HAS_DELIVERY_MODE=ParameterDetails(
    _(u'Sales'),
    _(u'Has Delivery Mode'),
    _(u'Does this branch work with delivery service? If not, the '
      'delivery option will be disable on Point of Sales Application.')),

    MAX_SEARCH_RESULTS=ParameterDetails(
    _(u'General'),
    _(u'Max Search Results'),
    _(u'The maximum number of results we must show after searching '
      'in any dialog.')),

    CONFIRM_SALES_ON_TILL=ParameterDetails(
    _(u'Sales'),
    _(u'Confirm Sales on Till'),
    _(u'Once this parameter is set, the sales confirmation are only made '
      'on till application and the fiscal coupon will be printed on '
      'that application instead of Point of Sales')),

    ACCEPT_CHANGE_SALESPERSON=ParameterDetails(
    _(u'Sales'),
    _(u'Accept Change Salesperson'),
    _(u'Once this parameter is set to true, the user will be '
      'able to change the salesperson of an opened '
      'order on sale checkout dialog')),

    RETURN_MONEY_ON_SALES=ParameterDetails(
    _(u'Sales'),
    _(u'Return Money On Sales'),
    _(u'Once this parameter is set the salesperson can return '
      'money to clients when there is overpaid values in sales '
      'with gift certificates as payment method.')),

    MAX_SALE_DISCOUNT=ParameterDetails(
    _(u'Sales'),
    _(u'Max discount for sales'),
    _(u'The max discount for salesperson in a sale')),

    SALE_PAY_COMMISSION_WHEN_CONFIRMED=ParameterDetails(
    _(u'Sales'),
    _(u'Commission Payment At Sale Confirmation'),
    _(u'Define whether the commission is paid when a sale is confirmed. '
       'If True pay the commission when a sale is confirmed, '
       'if False, pay a relative commission for each commission when '
       'the sales payment is paid.')),


    # XXX: These parameters are Brazil-specific
    ASK_SALES_CFOP=ParameterDetails(
    _(u'Sales'),
    _(u'Ask for Sale Order CFOP'),
    _(u'Once this parameter is set to True we will ask for the CFOP '
      'when creating new sale orders')),

    DEFAULT_SALES_CFOP=ParameterDetails(
    _(u'Sales'),
    _(u'Default Sales CFOP'),
    _(u'Default CFOP (Fiscal Code of Operations) used when generating '
      'fiscal book entries.')),

    DEFAULT_RETURN_SALES_CFOP=ParameterDetails(
    _(u'Sales'),
    _(u'Default Return Sales CFOP'),
    _(u'Default CFOP (Fiscal Code of Operations) used when returning '
      'sale orders ')),

    DEFAULT_RECEIVING_CFOP=ParameterDetails(
    _(u'Purchase'),
    _(u'Default Receiving CFOP'),
    _(u'Default CFOP (Fiscal Code of Operations) used when receiving '
      'products in the stock application.')),

    ICMS_TAX=ParameterDetails(
    _(u'Sales'),
    _(u'Default ICMS tax'),
    _(u'Default ICMS to be applied on all the products of a sale. '
      'Note that this a percentage value and must be set as the '
      '0 &amp;lt; value &amp;lt; 100. E.g: 18, which means 18% of tax.')),

    ISS_TAX=ParameterDetails(
    _(u'Sales'),
    _(u'Default ISS tax'),
    _(u'Default ISS to be applied on all the services of a sale. '
      'Note that this a percentage value and must be set as the '
      '0 &amp;lt; value &amp;lt; 100. E.g: 12, which means 12% of tax.')),

    SUBSTITUTION_TAX=ParameterDetails(
    _(u'Sales'),
    _(u'Default Substitution tax'),
    _(u'The tax applied on all sale products with substitution tax type. '
      'Note that this a percentage value and must be set as the format: '
      '0 &amp;lt; value &amp;lt; 100. E.g: 16, which means 16% of tax.')),

    DEFAULT_AREA_CODE=ParameterDetails(
    _(u'General'),
    _(u'Default area code'),
    _(u'This is the default area code which will be used when '
      'registering new clients, users and more to the system')),

    DEFAULT_PRODUCT_TAX_CONSTANT=ParameterDetails(
    _(u'Sales'),
    _(u'Default tax constant for products'),
    _(u'This is the default tax constant which will be used '
      'when adding new products to the system')),

    CAT52_DEST_DIR=ParameterDetails(
    _(u'General'),
    _(u'Cat 52 destination directory'),
    _(u'Where the file generated after a Z-reduction should be saved.')),

    USE_FOUR_PRECISION_DIGITS=ParameterDetails(
    _(u'General'),
    _(u'Use four precision digits'),
    _(u'Once this parameter is set, the products cost will be expressed '
       'using four precision digits.')),

    NFE_SERIAL_NUMBER=ParameterDetails(
    _(u'NF-e'),
    _(u'Fiscal document serial number'),
    _(u'Fiscal document serial number. Fill with 0 if the NF-e have no '
       'series. This parameter only has effect if the nfe plugin is enabled.')),

    NFE_DANFE_ORIENTATION=ParameterDetails(
    _(u'NF-e'),
    _(u'Danfe printing orientation'),
    _(u'Orientation to use for printing danfe. Portrait or Landscape')),

    )

class ParameterAttr:
    def __init__(self, key, type, initial=None, options=None):
        self.key = key
        self.type = type
        self.initial = initial
        self.options = options

    def get_parameter_type(self):
        if isinstance(self.type, basestring):
            return namedAny('stoqlib.domain.' + self.type)
        else:
            return self.type


class ParameterAccess(ClassInittableObject):
    """A mechanism to tie specific instances to constants that can be
    made available cross-application. This class has a special hook that
    allows the values to be looked up on-the-fly and cached.

    Usage:

    >>> from stoqlib.lib.parameters import sysparam
    >>> from stoqlib.database.runtime import get_connection
    >>> conn = get_connection()
    >>> parameter = sysparam(conn).parameter_name
    """

    # New parameters must always be defined here
    constants = [
        # Adding constants
        ParameterAttr('EDIT_CODE_PRODUCT', bool, initial=False),
        ParameterAttr('USE_LOGIC_QUANTITY', bool, initial=True),
        ParameterAttr('POS_FULL_SCREEN', bool, initial=False),
        ParameterAttr('HAS_DELIVERY_MODE', bool, initial=True),
        ParameterAttr('ACCEPT_CHANGE_SALESPERSON', bool, initial=False),
        ParameterAttr('ENABLE_PAULISTA_INVOICE', bool, initial=False),
        ParameterAttr('MAX_SEARCH_RESULTS', int, initial=600),
        ParameterAttr('CITY_SUGGESTED', unicode, initial=u'Sao Carlos'),
        ParameterAttr('STATE_SUGGESTED', unicode, initial=u'SP'),
        ParameterAttr('COUNTRY_SUGGESTED', unicode, initial=u'Brazil'),
        ParameterAttr('CONFIRM_SALES_ON_TILL', bool, initial=False),
        ParameterAttr('RETURN_MONEY_ON_SALES', bool, initial=True),
        ParameterAttr('ASK_SALES_CFOP', bool, initial=False),
        ParameterAttr('MAX_SALE_DISCOUNT', int, initial=5),
        ParameterAttr('ICMS_TAX', Decimal, initial=18),
        ParameterAttr('ISS_TAX', Decimal, initial=18),
        ParameterAttr('SUBSTITUTION_TAX', Decimal, initial=18),
        ParameterAttr('POS_SEPARATE_CASHIER', bool, initial=False),
        ParameterAttr('DEFAULT_AREA_CODE', int, initial=16),
        ParameterAttr('SALE_PAY_COMMISSION_WHEN_CONFIRMED', bool,
                       initial=False),
        ParameterAttr('CUSTOM_LOGO_FOR_REPORTS', ImageHelper, initial=''),
        ParameterAttr('CAT52_DEST_DIR', DirectoryParameter, initial='~/.stoq/cat52'),
        ParameterAttr('ALLOW_OUTDATED_PURCHASES', bool, initial=False),
        ParameterAttr('USE_FOUR_PRECISION_DIGITS', bool, initial=False),
        ParameterAttr('DISABLE_COOKIES', bool, initial=False),
        ParameterAttr('NFE_SERIAL_NUMBER', int, initial=1),
        ParameterAttr('NFE_DANFE_ORIENTATION', int, initial=0,
                      options={0: _(u'Portrait'),
                               1: _(u'Landscape')}
                               ),
        # Adding objects -- Note that all the object referred here must
        # implements the IDescribable interface.
        ParameterAttr('DEFAULT_SALES_CFOP', u'fiscal.CfopData'),
        ParameterAttr('DEFAULT_RETURN_SALES_CFOP', u'fiscal.CfopData'),
        ParameterAttr('DEFAULT_RECEIVING_CFOP', u'fiscal.CfopData'),
        ParameterAttr('SUGGESTED_SUPPLIER',
                      u'person.PersonAdaptToSupplier'),
        ParameterAttr('SUGGESTED_UNIT',
                      u'sellable.SellableUnit'),
        ParameterAttr('MAIN_COMPANY',
                      u'person.PersonAdaptToBranch'),
        ParameterAttr('DEFAULT_BASE_CATEGORY',
                      u'sellable.SellableCategory'),
        ParameterAttr('DEFAULT_SALESPERSON_ROLE',
                      u'person.EmployeeRole'),
        ParameterAttr('DEFAULT_PAYMENT_DESTINATION',
                      u'payment.destination.PaymentDestination'),
        ParameterAttr('DELIVERY_SERVICE',
                      u'sellable.Sellable'),
        ParameterAttr('DEFAULT_PRODUCT_TAX_CONSTANT',
                      u'sellable.SellableTaxConstant'),
        ]

    _cache = {}

    @classmethod
    def __class_init__(cls, namespace):
        for obj in cls.constants:
            getter = lambda self, n=obj.key, v=obj.type: (
                self.get_parameter_by_field(n, v))
            setter = lambda self, value, n=obj.key: (
                self._set_schema(n, value))
            prop = property(getter, setter)
            setattr(cls, obj.key, prop)

    def __init__(self, conn):
        ClassInittableObject.__init__(self)
        self.conn = conn

    def _remove_unused_parameters(self):
        """Remove any  parameter found in ParameterData table which is not
        used any longer.
        """
        global _parameter_info
        for param in ParameterData.select(connection=self.conn):
            if param.field_name not in _parameter_info.keys():
                ParameterData.delete(param.id, connection=self.conn)

    def _set_schema(self, field_name, field_value, is_editable=True):
        if field_value is not None:
            field_value = unicode(field_value)

        data = ParameterData.selectOneBy(connection=self.conn,
                                         field_name=field_name)
        if data is None:
            ParameterData(connection=self.conn,
                          field_name=field_name,
                          field_value=field_value,
                          is_editable=is_editable)
        else:
            data.field_value = field_value

    #
    # Public API
    #

    @argcheck(str, object)
    def update_parameter(self, parameter_name, value):
        param = get_parameter_by_field(parameter_name, self.conn)
        param.field_value = unicode(value)
        self.rebuild_cache_for(parameter_name)

    def rebuild_cache_for(self, param_name):
        from stoqlib.domain.base import AbstractModel
        try:
            value = self._cache[param_name]
        except KeyError:
            return

        param = get_parameter_by_field(param_name, self.conn)
        value_type = type(value)
        if not issubclass(value_type, AbstractModel):
            # XXX: workaround to works with boolean types:
            data = param.field_value
            if value_type is bool:
                data = int(data)
            self._cache[param_name] = value_type(data)
            return
        table = value_type
        obj_id = param.field_value
        self._cache[param_name] = table.get(obj_id, connection=self.conn)

    def rebuild_cache(self):
        map(self.rebuild_cache_for, self._cache.keys())

    def clear_cache(self):
        log.info("Clearing cache")
        ParameterAccess._cache = {}

    def get_parameter_constant(self, field_name):
        for constant in ParameterAccess.constants:
            if constant.key == field_name:
                return constant
        else:
            raise KeyError("No such a parameter: %s" % (field_name,))

    def get_parameter_type(self, field_name):
        constant = self.get_parameter_constant(field_name)

        if isinstance(constant.type, basestring):
            return namedAny('stoqlib.domain.' + constant.type)
        else:
            return constant.type

    def get_parameter_by_field(self, field_name, field_type):
        from stoqlib.domain.base import AbstractModel
        if isinstance(field_type, unicode):
            field_type = namedAny('stoqlib.domain.' + field_type)
        if self._cache.has_key(field_name):
            param = self._cache[field_name]
            if issubclass(field_type, AbstractModel):
                return field_type.get(param.id, connection=self.conn)
            elif issubclass(field_type, (ImageHelper, DirectoryParameter)):
               return param
            else:
                return field_type(param)
        value = ParameterData.selectOneBy(field_name=field_name,
                                          connection=self.conn)
        if value is None:
            return
        if issubclass(field_type, AbstractModel):
            if value.field_value == '' or value.field_value is None:
                return
            param = field_type.get(value.field_value, connection=self.conn)
        else:
            # XXX: workaround to works with boolean types:
            value = value.field_value
            if field_type is bool:
                if value == 'True':
                    value = True
                elif value == 'False':
                    value = False
                else:
                    value = bool(int(value))
            param = field_type(value)
        self._cache[field_name] = param
        return param

    def set_defaults(self, update=False):
        self._remove_unused_parameters()
        constants = [c for c in self.constants if c.initial is not None]

        # Creating constants
        for obj in constants:
            if (update and self.get_parameter_by_field(obj.key, obj.type)
                is not None):
                continue

            if obj.type is bool:
                # Convert Bool to int here
                value = int(obj.initial)
            else:
                value = obj.initial
            self._set_schema(obj.key, value)

        # Creating system objects
        # When creating new methods for system objects creation add them
        # always here
        self.ensure_default_sales_cfop()
        self.ensure_default_return_sales_cfop()
        self.ensure_default_receiving_cfop()
        self.ensure_suggested_supplier()
        self.ensure_suggested_unit()
        self.ensure_default_base_category()
        self.ensure_default_salesperson_role()
        self.ensure_main_company()
        self.ensure_payment_destination()
        self.ensure_delivery_service()
        self.ensure_product_tax_constant()

    #
    # Methods for system objects creation
    #

    def ensure_suggested_supplier(self):
        key = "SUGGESTED_SUPPLIER"
        from stoqlib.domain.person import Person
        if self.get_parameter_by_field(key, Person.getAdapterClass(ISupplier)):
            return
        self._set_schema(key, None)

    def ensure_suggested_unit(self):
        key = "SUGGESTED_UNIT"
        from stoqlib.domain.sellable import SellableUnit
        if self.get_parameter_by_field(key, SellableUnit):
            return
        self._set_schema(key, None)

    def ensure_default_base_category(self):
        from stoqlib.domain.sellable import SellableCategory
        key = "DEFAULT_BASE_CATEGORY"
        if self.get_parameter_by_field(key, SellableCategory):
            return
        base_category = SellableCategory(description=key,
                                         connection=self.conn)
        self._set_schema(key, base_category.id)

    def ensure_default_salesperson_role(self):
        from stoqlib.domain.person import EmployeeRole
        key = "DEFAULT_SALESPERSON_ROLE"
        if self.get_parameter_by_field(key, EmployeeRole):
            return
        role = EmployeeRole(name=u'Salesperson',
                            connection=self.conn)
        self._set_schema(key, role.id, is_editable=False)

    def ensure_main_company(self):
        from stoqlib.domain.person import Person
        key = "MAIN_COMPANY"
        if self.get_parameter_by_field(key, Person.getAdapterClass(IBranch)):
            return
        self._set_schema(key, None)

    def ensure_payment_destination(self):
        # Note that this method must always be called after
        # ensure_main_company
        from stoqlib.domain.payment.destination import PaymentDestination
        key = "DEFAULT_PAYMENT_DESTINATION"
        if self.get_parameter_by_field(key, PaymentDestination):
            return
        branch = self.MAIN_COMPANY
        pm = PaymentDestination(description=_(u'Default Store Destination'),
                                branch=branch,
                                connection=self.conn)
        self._set_schema(key, pm.id)

    def ensure_delivery_service(self):
        from stoqlib.domain.sellable import (BaseSellableInfo,
                                             Sellable,
                                             SellableTaxConstant)
        from stoqlib.domain.service import Service
        key = "DELIVERY_SERVICE"
        if self.get_parameter_by_field(key, Sellable):
            return

        tax_constant = SellableTaxConstant.get_by_type(TaxType.SERVICE, self.conn)
        sellable_info = BaseSellableInfo(connection=self.conn,
                                         description=_(u'Delivery'))
        sellable = Sellable(tax_constant=tax_constant,
                            base_sellable_info=sellable_info,
                            connection=self.conn)
        service = Service(sellable=sellable, connection=self.conn)
        self._set_schema(key, sellable.id)

    def _ensure_cfop(self, key, description, code):
        from stoqlib.domain.fiscal import CfopData
        if self.get_parameter_by_field(key, CfopData):
            return
        data = CfopData(code=code, description=description,
                        connection=self.conn)
        self._set_schema(key, data.id)

    def ensure_default_return_sales_cfop(self):
        self._ensure_cfop("DEFAULT_RETURN_SALES_CFOP",
                          u"Devolucao",
                          u"5.202")

    def ensure_default_sales_cfop(self):
        self._ensure_cfop("DEFAULT_SALES_CFOP",
                          u"Venda de Mercadoria Adquirida",
                          u"5.102")

    def ensure_default_receiving_cfop(self):
        self._ensure_cfop("DEFAULT_RECEIVING_CFOP",
                          u"Compra para Comercializacao",
                          u"1.102")

    def ensure_product_tax_constant(self):
        from stoqlib.domain.sellable import SellableTaxConstant
        key = "DEFAULT_PRODUCT_TAX_CONSTANT"
        if self.get_parameter_by_field(key, SellableTaxConstant):
            return

        tax_constant = SellableTaxConstant.get_by_type(TaxType.NONE, self.conn)
        self._set_schema(key, tax_constant.id)


#
# General routines
#


def sysparam(conn):
    return ParameterAccess(conn)


# FIXME: Move to a classmethod on ParameterData
def get_parameter_by_field(field_name, conn):
    data = ParameterData.selectOneBy(field_name=field_name,
                                     connection=conn)
    if data is None:
        raise DatabaseInconsistency(
            "Can't find a ParameterData object for the key %s" %
            field_name)
    return data


def get_foreign_key_parameter(field_name, conn):
    parameter = get_parameter_by_field(field_name, conn)
    if not (parameter and parameter.foreign_key):
        msg = _('There is no defined %s parameter data'
                'in the database.' % field_name)
        raise DatabaseInconsistency(msg)
    return parameter


def get_parameter_details(field_name):
    """ Returns a ParameterDetails class for the given parameter name, or
    None if the name supplied isn't a valid parameter name.
    """
    global _parameter_info
    try:
        return _parameter_info[field_name]
    except KeyError:
        raise NameError("Does not exists no parameters "
                        "with name %s" % field_name)


#
# Ensuring everything
#

def check_parameter_presence(conn):
    """Check so the number of installed parameters are equal to
    the number of available ones
    @returns: True if they're up to date, False otherwise
    """

    global _parameter_info
    results = ParameterData.select(connection=conn)

    return results.count() == len(_parameter_info)

def ensure_system_parameters(update=False):
    log.info("Creating default system parameters")
    trans = new_transaction()
    param = sysparam(trans)
    param.set_defaults(update)
    trans.commit(close=True)
