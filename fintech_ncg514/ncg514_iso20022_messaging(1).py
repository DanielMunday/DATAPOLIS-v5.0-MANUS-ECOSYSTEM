"""
DATAPOLIS v3.0 - NCG 514 ISO 20022 FINANCIAL MESSAGING
======================================================
Implementación de mensajería financiera ISO 20022 para Open Finance Chile
Según NCG 514 CMF - Deadline Abril 2026

Autor: DATAPOLIS SpA
Versión: 1.0.0
Fecha: 2026-02-01
Estándar: ISO 20022 Universal Financial Industry Message Scheme
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any, Union
from enum import Enum
from decimal import Decimal
import hashlib
import secrets
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
from abc import ABC, abstractmethod


# ============================================================================
# ENUMERACIONES ISO 20022
# ============================================================================

class ISO20022MessageType(Enum):
    """Tipos de mensajes ISO 20022 soportados en SFA Chile"""
    # Account Information
    CAMT_052 = "camt.052"  # Bank to Customer Account Report
    CAMT_053 = "camt.053"  # Bank to Customer Statement
    CAMT_054 = "camt.054"  # Bank to Customer Debit/Credit Notification
    
    # Payment Initiation
    PAIN_001 = "pain.001"  # Customer Credit Transfer Initiation
    PAIN_002 = "pain.002"  # Customer Payment Status Report
    PAIN_007 = "pain.007"  # Customer Payment Reversal
    PAIN_008 = "pain.008"  # Customer Direct Debit Initiation
    
    # Payment Clearing and Settlement
    PACS_002 = "pacs.002"  # FI to FI Payment Status Report
    PACS_004 = "pacs.004"  # Payment Return
    PACS_008 = "pacs.008"  # FI to FI Customer Credit Transfer
    
    # Administration
    ADMI_002 = "admi.002"  # Message Reject
    ADMI_004 = "admi.004"  # System Event Notification


class PaymentMethod(Enum):
    """Métodos de pago según ISO 20022"""
    TRF = "TRF"    # Credit Transfer
    TRA = "TRA"    # Credit Transfer Advance
    DD = "DD"      # Direct Debit
    CHK = "CHK"    # Cheque
    CARD = "CARD"  # Card Payment


class TransactionStatus(Enum):
    """Estados de transacción ISO 20022"""
    ACTC = "ACTC"  # Accepted Technical Validation
    ACCP = "ACCP"  # Accepted Customer Profile
    ACSP = "ACSP"  # Accepted Settlement In Process
    ACSC = "ACSC"  # Accepted Settlement Completed
    ACWC = "ACWC"  # Accepted With Change
    PART = "PART"  # Partially Accepted
    PDNG = "PDNG"  # Pending
    RCVD = "RCVD"  # Received
    RJCT = "RJCT"  # Rejected


class CurrencyCode(Enum):
    """Códigos de moneda ISO 4217"""
    CLP = "CLP"  # Peso Chileno
    CLF = "CLF"  # Unidad de Fomento
    USD = "USD"  # US Dollar
    EUR = "EUR"  # Euro


class AccountType(Enum):
    """Tipos de cuenta ISO 20022"""
    CACC = "CACC"  # Current Account (Cuenta Corriente)
    SVGS = "SVGS"  # Savings Account (Cuenta de Ahorro)
    TRAN = "TRAN"  # Transit Account
    LOAN = "LOAN"  # Loan Account
    CARD = "CARD"  # Card Account (Tarjeta de Crédito)


class CreditDebitIndicator(Enum):
    """Indicador Crédito/Débito"""
    CRDT = "CRDT"  # Credit
    DBIT = "DBIT"  # Debit


class BalanceType(Enum):
    """Tipos de saldo ISO 20022"""
    OPBD = "OPBD"  # Opening Booked
    CLBD = "CLBD"  # Closing Booked
    OPAV = "OPAV"  # Opening Available
    CLAV = "CLAV"  # Closing Available
    PRCD = "PRCD"  # Previously Closed Booked
    ITAV = "ITAV"  # Interim Available
    ITBD = "ITBD"  # Interim Booked


class RejectReasonCode(Enum):
    """Códigos de rechazo ISO 20022"""
    AC01 = "AC01"  # Incorrect Account Number
    AC04 = "AC04"  # Closed Account Number
    AC06 = "AC06"  # Blocked Account
    AG01 = "AG01"  # Transaction Forbidden
    AG02 = "AG02"  # Invalid Bank Operation Code
    AM01 = "AM01"  # Zero Amount
    AM02 = "AM02"  # Not Allowed Amount
    AM03 = "AM03"  # Not Allowed Currency
    AM04 = "AM04"  # Insufficient Funds
    AM05 = "AM05"  # Duplicate
    BE01 = "BE01"  # Inconsistent with End Customer
    DT01 = "DT01"  # Invalid Date
    FF01 = "FF01"  # Invalid File Format
    RC01 = "RC01"  # Bank Identifier Incorrect
    RR01 = "RR01"  # Regulatory Reason
    CUST = "CUST"  # Requested by Customer
    TECH = "TECH"  # Technical Problem


# ============================================================================
# DATACLASSES - ESTRUCTURAS ISO 20022
# ============================================================================

@dataclass
class MonetaryAmount:
    """Monto monetario ISO 20022"""
    amount: Decimal
    currency: CurrencyCode
    
    def to_xml_element(self, tag_name: str) -> ET.Element:
        elem = ET.Element(tag_name)
        elem.set("Ccy", self.currency.value)
        elem.text = f"{self.amount:.2f}"
        return elem
    
    @classmethod
    def from_xml_element(cls, elem: ET.Element) -> 'MonetaryAmount':
        return cls(
            amount=Decimal(elem.text),
            currency=CurrencyCode(elem.get("Ccy"))
        )


@dataclass
class AccountIdentification:
    """Identificación de cuenta ISO 20022"""
    iban: Optional[str] = None
    other_id: Optional[str] = None  # Para cuentas chilenas sin IBAN
    account_type: Optional[AccountType] = None
    currency: Optional[CurrencyCode] = None
    name: Optional[str] = None
    
    def to_xml_element(self) -> ET.Element:
        acct = ET.Element("Acct")
        acct_id = ET.SubElement(acct, "Id")
        
        if self.iban:
            ET.SubElement(acct_id, "IBAN").text = self.iban
        elif self.other_id:
            othr = ET.SubElement(acct_id, "Othr")
            ET.SubElement(othr, "Id").text = self.other_id
        
        if self.account_type:
            ET.SubElement(acct, "Tp").text = self.account_type.value
        if self.currency:
            ET.SubElement(acct, "Ccy").text = self.currency.value
        if self.name:
            ET.SubElement(acct, "Nm").text = self.name
        
        return acct


@dataclass
class PartyIdentification:
    """Identificación de parte (persona/empresa) ISO 20022"""
    name: str
    postal_address: Optional[Dict[str, str]] = None
    identification: Optional[Dict[str, str]] = None  # RUT, passport, etc.
    contact_details: Optional[Dict[str, str]] = None
    
    def to_xml_element(self, tag_name: str) -> ET.Element:
        party = ET.Element(tag_name)
        ET.SubElement(party, "Nm").text = self.name
        
        if self.postal_address:
            addr = ET.SubElement(party, "PstlAdr")
            for key, value in self.postal_address.items():
                ET.SubElement(addr, key).text = value
        
        if self.identification:
            id_elem = ET.SubElement(party, "Id")
            if "rut" in self.identification:
                prvt_id = ET.SubElement(id_elem, "PrvtId")
                othr = ET.SubElement(prvt_id, "Othr")
                ET.SubElement(othr, "Id").text = self.identification["rut"]
                schme = ET.SubElement(othr, "SchmeNm")
                ET.SubElement(schme, "Cd").text = "TXID"  # Tax ID
        
        return party


@dataclass
class BankTransactionCode:
    """Código de transacción bancaria ISO 20022"""
    domain: str
    family: str
    sub_family: str
    proprietary: Optional[str] = None
    
    def to_xml_element(self) -> ET.Element:
        btc = ET.Element("BkTxCd")
        domn = ET.SubElement(btc, "Domn")
        ET.SubElement(domn, "Cd").text = self.domain
        fmly = ET.SubElement(domn, "Fmly")
        ET.SubElement(fmly, "Cd").text = self.family
        ET.SubElement(fmly, "SubFmlyCd").text = self.sub_family
        
        if self.proprietary:
            prtry = ET.SubElement(btc, "Prtry")
            ET.SubElement(prtry, "Cd").text = self.proprietary
        
        return btc


@dataclass
class Balance:
    """Saldo de cuenta ISO 20022"""
    type: BalanceType
    amount: MonetaryAmount
    credit_debit: CreditDebitIndicator
    date: date
    
    def to_xml_element(self) -> ET.Element:
        bal = ET.Element("Bal")
        
        tp = ET.SubElement(bal, "Tp")
        cd_or_prtry = ET.SubElement(tp, "CdOrPrtry")
        ET.SubElement(cd_or_prtry, "Cd").text = self.type.value
        
        bal.append(self.amount.to_xml_element("Amt"))
        ET.SubElement(bal, "CdtDbtInd").text = self.credit_debit.value
        
        dt = ET.SubElement(bal, "Dt")
        ET.SubElement(dt, "Dt").text = self.date.isoformat()
        
        return bal


@dataclass
class TransactionEntry:
    """Entrada de transacción ISO 20022 (camt.053/054)"""
    entry_reference: str
    amount: MonetaryAmount
    credit_debit: CreditDebitIndicator
    status: TransactionStatus
    booking_date: date
    value_date: date
    bank_transaction_code: BankTransactionCode
    
    # Detalles opcionales
    debtor: Optional[PartyIdentification] = None
    debtor_account: Optional[AccountIdentification] = None
    creditor: Optional[PartyIdentification] = None
    creditor_account: Optional[AccountIdentification] = None
    remittance_info: Optional[str] = None
    end_to_end_id: Optional[str] = None
    
    def to_xml_element(self) -> ET.Element:
        ntry = ET.Element("Ntry")
        
        ET.SubElement(ntry, "NtryRef").text = self.entry_reference
        ntry.append(self.amount.to_xml_element("Amt"))
        ET.SubElement(ntry, "CdtDbtInd").text = self.credit_debit.value
        ET.SubElement(ntry, "Sts").text = self.status.value
        
        bkg_dt = ET.SubElement(ntry, "BookgDt")
        ET.SubElement(bkg_dt, "Dt").text = self.booking_date.isoformat()
        
        val_dt = ET.SubElement(ntry, "ValDt")
        ET.SubElement(val_dt, "Dt").text = self.value_date.isoformat()
        
        ntry.append(self.bank_transaction_code.to_xml_element())
        
        # Detalles de transacción
        ntry_dtls = ET.SubElement(ntry, "NtryDtls")
        tx_dtls = ET.SubElement(ntry_dtls, "TxDtls")
        
        if self.end_to_end_id:
            refs = ET.SubElement(tx_dtls, "Refs")
            ET.SubElement(refs, "EndToEndId").text = self.end_to_end_id
        
        if self.debtor:
            rltd_pties = ET.SubElement(tx_dtls, "RltdPties")
            rltd_pties.append(self.debtor.to_xml_element("Dbtr"))
            if self.debtor_account:
                rltd_pties.append(self.debtor_account.to_xml_element())
        
        if self.creditor:
            rltd_pties = tx_dtls.find("RltdPties") or ET.SubElement(tx_dtls, "RltdPties")
            rltd_pties.append(self.creditor.to_xml_element("Cdtr"))
            if self.creditor_account:
                rltd_pties.append(self.creditor_account.to_xml_element())
        
        if self.remittance_info:
            rmt_inf = ET.SubElement(tx_dtls, "RmtInf")
            ET.SubElement(rmt_inf, "Ustrd").text = self.remittance_info
        
        return ntry


@dataclass
class PaymentInstruction:
    """Instrucción de pago ISO 20022 (pain.001)"""
    payment_info_id: str
    payment_method: PaymentMethod
    requested_execution_date: date
    debtor: PartyIdentification
    debtor_account: AccountIdentification
    debtor_agent: str  # BIC
    
    credit_transfers: List[Dict[str, Any]] = field(default_factory=list)
    batch_booking: bool = True
    number_of_transactions: int = 0
    control_sum: Decimal = Decimal("0")
    
    def add_credit_transfer(
        self,
        end_to_end_id: str,
        amount: MonetaryAmount,
        creditor: PartyIdentification,
        creditor_account: AccountIdentification,
        creditor_agent: str,
        remittance_info: Optional[str] = None
    ):
        """Agrega una transferencia de crédito a la instrucción"""
        self.credit_transfers.append({
            "end_to_end_id": end_to_end_id,
            "amount": amount,
            "creditor": creditor,
            "creditor_account": creditor_account,
            "creditor_agent": creditor_agent,
            "remittance_info": remittance_info
        })
        self.number_of_transactions += 1
        self.control_sum += amount.amount


# ============================================================================
# GENERADOR DE MENSAJES ISO 20022
# ============================================================================

class ISO20022MessageGenerator:
    """
    Generador de mensajes ISO 20022 para NCG 514
    """
    
    NAMESPACE = "urn:iso:std:iso:20022:tech:xsd"
    
    def __init__(self, participant_bic: str, participant_name: str):
        self.participant_bic = participant_bic
        self.participant_name = participant_name
    
    def _create_message_root(self, message_type: ISO20022MessageType) -> ET.Element:
        """Crea el elemento raíz del mensaje"""
        namespace = f"{self.NAMESPACE}:{message_type.value}.001.09"
        root = ET.Element("Document", xmlns=namespace)
        return root
    
    def _create_group_header(
        self,
        message_id: str,
        creation_datetime: datetime,
        number_of_transactions: int = 1,
        control_sum: Optional[Decimal] = None
    ) -> ET.Element:
        """Crea el header del grupo de mensajes"""
        grp_hdr = ET.Element("GrpHdr")
        
        ET.SubElement(grp_hdr, "MsgId").text = message_id
        ET.SubElement(grp_hdr, "CreDtTm").text = creation_datetime.isoformat()
        ET.SubElement(grp_hdr, "NbOfTxs").text = str(number_of_transactions)
        
        if control_sum is not None:
            ET.SubElement(grp_hdr, "CtrlSum").text = f"{control_sum:.2f}"
        
        # Initiating party
        init_pty = ET.SubElement(grp_hdr, "InitgPty")
        ET.SubElement(init_pty, "Nm").text = self.participant_name
        
        return grp_hdr
    
    # -------------------------------------------------------------------------
    # PAIN.001 - Customer Credit Transfer Initiation
    # -------------------------------------------------------------------------
    
    def generate_pain_001(
        self,
        payment_instruction: PaymentInstruction,
        message_id: Optional[str] = None
    ) -> str:
        """
        Genera mensaje pain.001 - Iniciación de Transferencia de Crédito
        Usado para PIS (Payment Initiation Services) en NCG 514
        """
        if not message_id:
            message_id = f"PAIN001-{secrets.token_hex(8).upper()}"
        
        root = self._create_message_root(ISO20022MessageType.PAIN_001)
        cstmr_cdt_trf_initn = ET.SubElement(root, "CstmrCdtTrfInitn")
        
        # Group Header
        grp_hdr = self._create_group_header(
            message_id=message_id,
            creation_datetime=datetime.now(),
            number_of_transactions=payment_instruction.number_of_transactions,
            control_sum=payment_instruction.control_sum
        )
        cstmr_cdt_trf_initn.append(grp_hdr)
        
        # Payment Information
        pmt_inf = ET.SubElement(cstmr_cdt_trf_initn, "PmtInf")
        ET.SubElement(pmt_inf, "PmtInfId").text = payment_instruction.payment_info_id
        ET.SubElement(pmt_inf, "PmtMtd").text = payment_instruction.payment_method.value
        ET.SubElement(pmt_inf, "BtchBookg").text = "true" if payment_instruction.batch_booking else "false"
        ET.SubElement(pmt_inf, "NbOfTxs").text = str(payment_instruction.number_of_transactions)
        ET.SubElement(pmt_inf, "CtrlSum").text = f"{payment_instruction.control_sum:.2f}"
        
        # Requested Execution Date
        reqd_exctn_dt = ET.SubElement(pmt_inf, "ReqdExctnDt")
        ET.SubElement(reqd_exctn_dt, "Dt").text = payment_instruction.requested_execution_date.isoformat()
        
        # Debtor
        pmt_inf.append(payment_instruction.debtor.to_xml_element("Dbtr"))
        pmt_inf.append(payment_instruction.debtor_account.to_xml_element())
        
        # Debtor Agent
        dbtr_agt = ET.SubElement(pmt_inf, "DbtrAgt")
        fin_instn_id = ET.SubElement(dbtr_agt, "FinInstnId")
        ET.SubElement(fin_instn_id, "BICFI").text = payment_instruction.debtor_agent
        
        # Credit Transfer Transaction Information
        for ct in payment_instruction.credit_transfers:
            cdt_trf_tx_inf = ET.SubElement(pmt_inf, "CdtTrfTxInf")
            
            # Payment ID
            pmt_id = ET.SubElement(cdt_trf_tx_inf, "PmtId")
            ET.SubElement(pmt_id, "EndToEndId").text = ct["end_to_end_id"]
            
            # Amount
            amt = ET.SubElement(cdt_trf_tx_inf, "Amt")
            amt.append(ct["amount"].to_xml_element("InstdAmt"))
            
            # Creditor Agent
            cdtr_agt = ET.SubElement(cdt_trf_tx_inf, "CdtrAgt")
            fin_instn_id = ET.SubElement(cdtr_agt, "FinInstnId")
            ET.SubElement(fin_instn_id, "BICFI").text = ct["creditor_agent"]
            
            # Creditor
            cdt_trf_tx_inf.append(ct["creditor"].to_xml_element("Cdtr"))
            cdt_trf_tx_inf.append(ct["creditor_account"].to_xml_element())
            
            # Remittance Information
            if ct.get("remittance_info"):
                rmt_inf = ET.SubElement(cdt_trf_tx_inf, "RmtInf")
                ET.SubElement(rmt_inf, "Ustrd").text = ct["remittance_info"]
        
        return self._format_xml(root)
    
    # -------------------------------------------------------------------------
    # PAIN.002 - Payment Status Report
    # -------------------------------------------------------------------------
    
    def generate_pain_002(
        self,
        original_message_id: str,
        original_message_type: ISO20022MessageType,
        status: TransactionStatus,
        transactions: List[Dict[str, Any]],
        message_id: Optional[str] = None
    ) -> str:
        """
        Genera mensaje pain.002 - Reporte de Estado de Pago
        """
        if not message_id:
            message_id = f"PAIN002-{secrets.token_hex(8).upper()}"
        
        root = self._create_message_root(ISO20022MessageType.PAIN_002)
        cstmr_pmt_sts_rpt = ET.SubElement(root, "CstmrPmtStsRpt")
        
        # Group Header
        grp_hdr = self._create_group_header(
            message_id=message_id,
            creation_datetime=datetime.now(),
            number_of_transactions=len(transactions)
        )
        cstmr_pmt_sts_rpt.append(grp_hdr)
        
        # Original Group Information
        orgnl_grp_inf = ET.SubElement(cstmr_pmt_sts_rpt, "OrgnlGrpInfAndSts")
        ET.SubElement(orgnl_grp_inf, "OrgnlMsgId").text = original_message_id
        ET.SubElement(orgnl_grp_inf, "OrgnlMsgNmId").text = original_message_type.value
        ET.SubElement(orgnl_grp_inf, "GrpSts").text = status.value
        
        # Transaction Information
        for tx in transactions:
            tx_inf = ET.SubElement(cstmr_pmt_sts_rpt, "OrgnlPmtInfAndSts")
            ET.SubElement(tx_inf, "OrgnlPmtInfId").text = tx.get("original_payment_id", "")
            ET.SubElement(tx_inf, "PmtInfSts").text = tx.get("status", status.value)
            
            if tx.get("reject_reason"):
                sts_rsn_inf = ET.SubElement(tx_inf, "StsRsnInf")
                rsn = ET.SubElement(sts_rsn_inf, "Rsn")
                ET.SubElement(rsn, "Cd").text = tx["reject_reason"]
                if tx.get("reject_info"):
                    ET.SubElement(sts_rsn_inf, "AddtlInf").text = tx["reject_info"]
        
        return self._format_xml(root)
    
    # -------------------------------------------------------------------------
    # CAMT.052 - Bank to Customer Account Report (Intraday)
    # -------------------------------------------------------------------------
    
    def generate_camt_052(
        self,
        account: AccountIdentification,
        balances: List[Balance],
        entries: List[TransactionEntry],
        from_datetime: datetime,
        to_datetime: datetime,
        message_id: Optional[str] = None
    ) -> str:
        """
        Genera mensaje camt.052 - Reporte de Cuenta (Intraday)
        Usado para AIS en NCG 514
        """
        if not message_id:
            message_id = f"CAMT052-{secrets.token_hex(8).upper()}"
        
        root = self._create_message_root(ISO20022MessageType.CAMT_052)
        bk_to_cstmr_acct_rpt = ET.SubElement(root, "BkToCstmrAcctRpt")
        
        # Group Header
        grp_hdr = self._create_group_header(
            message_id=message_id,
            creation_datetime=datetime.now()
        )
        bk_to_cstmr_acct_rpt.append(grp_hdr)
        
        # Report
        rpt = ET.SubElement(bk_to_cstmr_acct_rpt, "Rpt")
        ET.SubElement(rpt, "Id").text = f"RPT-{secrets.token_hex(6).upper()}"
        
        # Report Creation DateTime
        ET.SubElement(rpt, "CreDtTm").text = datetime.now().isoformat()
        
        # Account
        rpt.append(account.to_xml_element())
        
        # Reporting Period
        fr_to_dt = ET.SubElement(rpt, "FrToDt")
        ET.SubElement(fr_to_dt, "FrDtTm").text = from_datetime.isoformat()
        ET.SubElement(fr_to_dt, "ToDtTm").text = to_datetime.isoformat()
        
        # Balances
        for balance in balances:
            rpt.append(balance.to_xml_element())
        
        # Transaction Summary
        txs_smry = ET.SubElement(rpt, "TxsSummry")
        total_credits = sum(
            e.amount.amount for e in entries 
            if e.credit_debit == CreditDebitIndicator.CRDT
        )
        total_debits = sum(
            e.amount.amount for e in entries 
            if e.credit_debit == CreditDebitIndicator.DBIT
        )
        
        ttl_cdt_ntries = ET.SubElement(txs_smry, "TtlCdtNtries")
        ET.SubElement(ttl_cdt_ntries, "NbOfNtries").text = str(
            len([e for e in entries if e.credit_debit == CreditDebitIndicator.CRDT])
        )
        ET.SubElement(ttl_cdt_ntries, "Sum").text = f"{total_credits:.2f}"
        
        ttl_dbt_ntries = ET.SubElement(txs_smry, "TtlDbtNtries")
        ET.SubElement(ttl_dbt_ntries, "NbOfNtries").text = str(
            len([e for e in entries if e.credit_debit == CreditDebitIndicator.DBIT])
        )
        ET.SubElement(ttl_dbt_ntries, "Sum").text = f"{total_debits:.2f}"
        
        # Entries
        for entry in entries:
            rpt.append(entry.to_xml_element())
        
        return self._format_xml(root)
    
    # -------------------------------------------------------------------------
    # CAMT.053 - Bank to Customer Statement (End of Day)
    # -------------------------------------------------------------------------
    
    def generate_camt_053(
        self,
        account: AccountIdentification,
        statement_date: date,
        opening_balance: Balance,
        closing_balance: Balance,
        entries: List[TransactionEntry],
        message_id: Optional[str] = None
    ) -> str:
        """
        Genera mensaje camt.053 - Estado de Cuenta (End of Day)
        Usado para AIS en NCG 514
        """
        if not message_id:
            message_id = f"CAMT053-{secrets.token_hex(8).upper()}"
        
        root = self._create_message_root(ISO20022MessageType.CAMT_053)
        bk_to_cstmr_stmt = ET.SubElement(root, "BkToCstmrStmt")
        
        # Group Header
        grp_hdr = self._create_group_header(
            message_id=message_id,
            creation_datetime=datetime.now()
        )
        bk_to_cstmr_stmt.append(grp_hdr)
        
        # Statement
        stmt = ET.SubElement(bk_to_cstmr_stmt, "Stmt")
        ET.SubElement(stmt, "Id").text = f"STMT-{statement_date.isoformat()}"
        ET.SubElement(stmt, "CreDtTm").text = datetime.now().isoformat()
        
        # Account
        stmt.append(account.to_xml_element())
        
        # Statement Date
        fr_to_dt = ET.SubElement(stmt, "FrToDt")
        ET.SubElement(fr_to_dt, "FrDtTm").text = f"{statement_date.isoformat()}T00:00:00"
        ET.SubElement(fr_to_dt, "ToDtTm").text = f"{statement_date.isoformat()}T23:59:59"
        
        # Balances
        stmt.append(opening_balance.to_xml_element())
        stmt.append(closing_balance.to_xml_element())
        
        # Entries
        for entry in entries:
            stmt.append(entry.to_xml_element())
        
        return self._format_xml(root)
    
    # -------------------------------------------------------------------------
    # CAMT.054 - Bank to Customer Debit/Credit Notification
    # -------------------------------------------------------------------------
    
    def generate_camt_054(
        self,
        account: AccountIdentification,
        entry: TransactionEntry,
        message_id: Optional[str] = None
    ) -> str:
        """
        Genera mensaje camt.054 - Notificación de Débito/Crédito
        Para notificaciones en tiempo real
        """
        if not message_id:
            message_id = f"CAMT054-{secrets.token_hex(8).upper()}"
        
        root = self._create_message_root(ISO20022MessageType.CAMT_054)
        bk_to_cstmr_dbt_cdt_ntfctn = ET.SubElement(root, "BkToCstmrDbtCdtNtfctn")
        
        # Group Header
        grp_hdr = self._create_group_header(
            message_id=message_id,
            creation_datetime=datetime.now()
        )
        bk_to_cstmr_dbt_cdt_ntfctn.append(grp_hdr)
        
        # Notification
        ntfctn = ET.SubElement(bk_to_cstmr_dbt_cdt_ntfctn, "Ntfctn")
        ET.SubElement(ntfctn, "Id").text = f"NTFCTN-{secrets.token_hex(6).upper()}"
        ET.SubElement(ntfctn, "CreDtTm").text = datetime.now().isoformat()
        
        # Account
        ntfctn.append(account.to_xml_element())
        
        # Entry
        ntfctn.append(entry.to_xml_element())
        
        return self._format_xml(root)
    
    # -------------------------------------------------------------------------
    # ADMI.002 - Message Reject
    # -------------------------------------------------------------------------
    
    def generate_admi_002(
        self,
        original_message_id: str,
        original_message_type: ISO20022MessageType,
        reject_reason: RejectReasonCode,
        additional_info: Optional[str] = None,
        message_id: Optional[str] = None
    ) -> str:
        """
        Genera mensaje admi.002 - Rechazo de Mensaje
        """
        if not message_id:
            message_id = f"ADMI002-{secrets.token_hex(8).upper()}"
        
        root = self._create_message_root(ISO20022MessageType.ADMI_002)
        msg_rjct = ET.SubElement(root, "MsgRjct")
        
        # Related Reference
        rltd_ref = ET.SubElement(msg_rjct, "RltdRef")
        ET.SubElement(rltd_ref, "Ref").text = original_message_id
        
        # Reason
        rsn = ET.SubElement(msg_rjct, "Rsn")
        rjctg_pty_rsn = ET.SubElement(rsn, "RjctgPtyRsn")
        ET.SubElement(rjctg_pty_rsn, "RjctgPtyRsnCd").text = reject_reason.value
        
        if additional_info:
            ET.SubElement(rjctg_pty_rsn, "AddtlInf").text = additional_info
        
        return self._format_xml(root)
    
    # -------------------------------------------------------------------------
    # Utilidades
    # -------------------------------------------------------------------------
    
    def _format_xml(self, root: ET.Element) -> str:
        """Formatea el XML con indentación"""
        rough_string = ET.tostring(root, encoding="unicode")
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding=None)


# ============================================================================
# PARSER DE MENSAJES ISO 20022
# ============================================================================

class ISO20022MessageParser:
    """
    Parser de mensajes ISO 20022
    """
    
    def parse(self, xml_content: str) -> Dict[str, Any]:
        """Parsea un mensaje ISO 20022 y extrae su contenido"""
        root = ET.fromstring(xml_content)
        
        # Detectar tipo de mensaje
        message_type = self._detect_message_type(root)
        
        if message_type == ISO20022MessageType.CAMT_053:
            return self._parse_camt_053(root)
        elif message_type == ISO20022MessageType.CAMT_052:
            return self._parse_camt_052(root)
        elif message_type == ISO20022MessageType.PAIN_001:
            return self._parse_pain_001(root)
        elif message_type == ISO20022MessageType.PAIN_002:
            return self._parse_pain_002(root)
        else:
            return {"message_type": message_type.value if message_type else "unknown"}
    
    def _detect_message_type(self, root: ET.Element) -> Optional[ISO20022MessageType]:
        """Detecta el tipo de mensaje ISO 20022"""
        namespace = root.tag.split("}")[0] + "}" if "}" in root.tag else ""
        
        # Buscar elemento hijo que indique el tipo
        for child in root:
            tag = child.tag.replace(namespace, "")
            if tag == "BkToCstmrStmt":
                return ISO20022MessageType.CAMT_053
            elif tag == "BkToCstmrAcctRpt":
                return ISO20022MessageType.CAMT_052
            elif tag == "CstmrCdtTrfInitn":
                return ISO20022MessageType.PAIN_001
            elif tag == "CstmrPmtStsRpt":
                return ISO20022MessageType.PAIN_002
        
        return None
    
    def _parse_camt_053(self, root: ET.Element) -> Dict[str, Any]:
        """Parsea mensaje camt.053"""
        result = {
            "message_type": "camt.053",
            "statements": []
        }
        
        # Namespace handling
        ns = {"iso": root.tag.split("}")[0].replace("{", "")} if "}" in root.tag else {}
        
        for stmt in root.findall(".//Stmt", ns) or root.findall(".//Stmt"):
            statement = {
                "id": self._get_text(stmt, "Id"),
                "creation_datetime": self._get_text(stmt, "CreDtTm"),
                "balances": [],
                "entries": []
            }
            
            # Parsear saldos
            for bal in stmt.findall(".//Bal", ns) or stmt.findall(".//Bal"):
                balance = {
                    "type": self._get_text(bal, ".//Cd"),
                    "amount": self._get_text(bal, ".//Amt"),
                    "currency": bal.find(".//Amt").get("Ccy") if bal.find(".//Amt") is not None else None,
                    "credit_debit": self._get_text(bal, "CdtDbtInd")
                }
                statement["balances"].append(balance)
            
            # Parsear entries
            for ntry in stmt.findall(".//Ntry", ns) or stmt.findall(".//Ntry"):
                entry = {
                    "reference": self._get_text(ntry, "NtryRef"),
                    "amount": self._get_text(ntry, ".//Amt"),
                    "credit_debit": self._get_text(ntry, "CdtDbtInd"),
                    "status": self._get_text(ntry, "Sts"),
                    "booking_date": self._get_text(ntry, ".//BookgDt/Dt"),
                    "value_date": self._get_text(ntry, ".//ValDt/Dt")
                }
                statement["entries"].append(entry)
            
            result["statements"].append(statement)
        
        return result
    
    def _parse_camt_052(self, root: ET.Element) -> Dict[str, Any]:
        """Parsea mensaje camt.052"""
        # Similar a camt.053 pero para reportes intraday
        return self._parse_camt_053(root)
    
    def _parse_pain_001(self, root: ET.Element) -> Dict[str, Any]:
        """Parsea mensaje pain.001"""
        result = {
            "message_type": "pain.001",
            "message_id": "",
            "payment_instructions": []
        }
        
        # Group Header
        grp_hdr = root.find(".//GrpHdr")
        if grp_hdr is not None:
            result["message_id"] = self._get_text(grp_hdr, "MsgId")
            result["creation_datetime"] = self._get_text(grp_hdr, "CreDtTm")
            result["number_of_transactions"] = self._get_text(grp_hdr, "NbOfTxs")
        
        # Payment Information
        for pmt_inf in root.findall(".//PmtInf"):
            instruction = {
                "payment_info_id": self._get_text(pmt_inf, "PmtInfId"),
                "payment_method": self._get_text(pmt_inf, "PmtMtd"),
                "debtor_name": self._get_text(pmt_inf, ".//Dbtr/Nm"),
                "credit_transfers": []
            }
            
            for cdt_trf in pmt_inf.findall(".//CdtTrfTxInf"):
                transfer = {
                    "end_to_end_id": self._get_text(cdt_trf, ".//EndToEndId"),
                    "amount": self._get_text(cdt_trf, ".//InstdAmt"),
                    "creditor_name": self._get_text(cdt_trf, ".//Cdtr/Nm")
                }
                instruction["credit_transfers"].append(transfer)
            
            result["payment_instructions"].append(instruction)
        
        return result
    
    def _parse_pain_002(self, root: ET.Element) -> Dict[str, Any]:
        """Parsea mensaje pain.002"""
        result = {
            "message_type": "pain.002",
            "original_message_id": "",
            "group_status": "",
            "transactions": []
        }
        
        # Original Group Info
        orgnl_grp = root.find(".//OrgnlGrpInfAndSts")
        if orgnl_grp is not None:
            result["original_message_id"] = self._get_text(orgnl_grp, "OrgnlMsgId")
            result["group_status"] = self._get_text(orgnl_grp, "GrpSts")
        
        return result
    
    def _get_text(self, element: ET.Element, path: str) -> Optional[str]:
        """Obtiene texto de un elemento o subelemento"""
        if path.startswith(".//"):
            found = element.find(path)
        else:
            found = element.find(path)
        return found.text if found is not None else None


# ============================================================================
# VALIDADOR DE MENSAJES ISO 20022
# ============================================================================

class ISO20022Validator:
    """
    Validador de mensajes ISO 20022 según NCG 514
    """
    
    def validate_pain_001(self, xml_content: str) -> Dict[str, Any]:
        """Valida mensaje pain.001"""
        errors = []
        warnings = []
        
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            return {"valid": False, "errors": [f"XML inválido: {str(e)}"]}
        
        # Validar Group Header
        grp_hdr = root.find(".//GrpHdr")
        if grp_hdr is None:
            errors.append("Falta GrpHdr (Group Header)")
        else:
            if grp_hdr.find("MsgId") is None:
                errors.append("Falta MsgId en GrpHdr")
            if grp_hdr.find("CreDtTm") is None:
                errors.append("Falta CreDtTm en GrpHdr")
        
        # Validar Payment Information
        pmt_inf = root.find(".//PmtInf")
        if pmt_inf is None:
            errors.append("Falta PmtInf (Payment Information)")
        else:
            if pmt_inf.find("PmtInfId") is None:
                errors.append("Falta PmtInfId en PmtInf")
            if pmt_inf.find("PmtMtd") is None:
                errors.append("Falta PmtMtd (Payment Method)")
            
            # Validar Debtor
            dbtr = pmt_inf.find("Dbtr")
            if dbtr is None:
                errors.append("Falta Dbtr (Debtor)")
            
            # Validar Credit Transfers
            cdt_trfs = pmt_inf.findall(".//CdtTrfTxInf")
            if not cdt_trfs:
                errors.append("Falta al menos un CdtTrfTxInf")
            
            for i, cdt_trf in enumerate(cdt_trfs):
                if cdt_trf.find(".//EndToEndId") is None:
                    errors.append(f"Falta EndToEndId en transacción {i+1}")
                if cdt_trf.find(".//InstdAmt") is None:
                    errors.append(f"Falta InstdAmt en transacción {i+1}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def validate_camt_053(self, xml_content: str) -> Dict[str, Any]:
        """Valida mensaje camt.053"""
        errors = []
        warnings = []
        
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            return {"valid": False, "errors": [f"XML inválido: {str(e)}"]}
        
        # Validar Statement
        stmt = root.find(".//Stmt")
        if stmt is None:
            errors.append("Falta Stmt (Statement)")
        else:
            if stmt.find("Id") is None:
                errors.append("Falta Id en Statement")
            
            # Validar Account
            acct = stmt.find("Acct")
            if acct is None:
                errors.append("Falta Acct (Account)")
            
            # Validar Balances
            balances = stmt.findall(".//Bal")
            if len(balances) < 2:
                warnings.append("Se recomienda incluir saldo de apertura y cierre")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    # Crear generador
    generator = ISO20022MessageGenerator(
        participant_bic="BABORCLRMXXX",
        participant_name="DATAPOLIS SpA"
    )
    
    # Crear instrucción de pago
    payment = PaymentInstruction(
        payment_info_id="PMT-001",
        payment_method=PaymentMethod.TRF,
        requested_execution_date=date.today() + timedelta(days=1),
        debtor=PartyIdentification(
            name="Juan Pérez",
            identification={"rut": "12.345.678-9"}
        ),
        debtor_account=AccountIdentification(
            other_id="0012345678",
            account_type=AccountType.CACC,
            currency=CurrencyCode.CLP
        ),
        debtor_agent="BABORCLRMXXX"
    )
    
    # Agregar transferencia
    payment.add_credit_transfer(
        end_to_end_id="E2E-001",
        amount=MonetaryAmount(Decimal("150000"), CurrencyCode.CLP),
        creditor=PartyIdentification(
            name="María González",
            identification={"rut": "98.765.432-1"}
        ),
        creditor_account=AccountIdentification(
            other_id="0098765432",
            account_type=AccountType.SVGS,
            currency=CurrencyCode.CLP
        ),
        creditor_agent="BABORCLRMYYY",
        remittance_info="Pago arriendo Febrero 2026"
    )
    
    # Generar pain.001
    pain001 = generator.generate_pain_001(payment)
    print("=== PAIN.001 ===")
    print(pain001[:2000])  # Primeros 2000 caracteres
    
    # Validar
    validator = ISO20022Validator()
    validation = validator.validate_pain_001(pain001)
    print("\n=== VALIDACIÓN ===")
    print(json.dumps(validation, indent=2))
