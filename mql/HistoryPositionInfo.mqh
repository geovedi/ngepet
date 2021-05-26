// https://www.mql5.com/en/code/viewcode/27683/229711/chistorypositioninfo.mqh

string TimeElapsedToString(const datetime pElapsedSeconds) {
  const long days = pElapsedSeconds / PeriodSeconds(PERIOD_D1);

  return ((days ? (string)days + "d " : "") +
          TimeToString(pElapsedSeconds, TIME_SECONDS));
}

class CHistoryPositionInfo : public CObject {
 protected:
  ulong m_curr_ticket;
  CArrayLong m_tickets;
  CDealInfo m_curr_deal;

 public:
  CHistoryPositionInfo(void);
  ~CHistoryPositionInfo(void);
  ulong Ticket(void) const { return (m_curr_ticket); }
  datetime TimeOpen(void);
  ulong TimeOpenMsc(void);
  datetime TimeClose(void);
  ulong TimeCloseMsc(void);
  ENUM_POSITION_TYPE PositionType(void);
  string TypeDescription(void);
  long Magic(void);
  long Identifier(void);
  ENUM_DEAL_REASON OpenReason(void);
  ENUM_DEAL_REASON CloseReason(void);
  double Volume(void);
  double PriceOpen(void);
  double StopLoss(void) const;
  double TakeProfit(void) const;
  double PriceClose(void);
  double Commission(void);
  double Swap(void);
  double Profit(void);
  string Symbol(void);
  string OpenComment(void);
  string CloseComment(void);
  string OpenReasonDescription(void);
  string CloseReasonDescription(void);
  string DealTickets(const string separator = " ");
  string FormatType(string& str, const uint type) const;
  string FormatReason(string& str, const uint reason) const;
  bool HistorySelect(datetime from_date, datetime to_date);
  int PositionsTotal(void) const;
  bool SelectByTicket(const ulong ticket);
  bool SelectByIndex(const int index);

 protected:
  bool HistoryPositionSelect(const long position_id) const;
  bool HistoryPositionCheck(const int log_level);
};

CHistoryPositionInfo::CHistoryPositionInfo(void) : m_curr_ticket(0) {
  ENUM_ACCOUNT_MARGIN_MODE margin_mode =
      (ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE);
  if (margin_mode != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING) {
    Print(__FUNCTION__ + " > Error: no retail hedging!");
  }
}

CHistoryPositionInfo::~CHistoryPositionInfo(void) {}

datetime CHistoryPositionInfo::TimeOpen(void) {
  datetime pos_time = 0;
  if (m_curr_ticket)
    if (m_curr_deal.SelectByIndex(0))
      pos_time = m_curr_deal.Time();
  return (pos_time);
}

ulong CHistoryPositionInfo::TimeOpenMsc(void) {
  ulong pos_time_msc = 0;
  if (m_curr_ticket)
    if (m_curr_deal.SelectByIndex(0))
      pos_time_msc = m_curr_deal.TimeMsc();
  return (pos_time_msc);
}

datetime CHistoryPositionInfo::TimeClose(void) {
  datetime pos_time = 0;
  //--- if valid selection
  if (m_curr_ticket)
    if (m_curr_deal.SelectByIndex(HistoryDealsTotal() - 1))
      pos_time = m_curr_deal.Time();
  return (pos_time);
}

ulong CHistoryPositionInfo::TimeCloseMsc(void) {
  ulong pos_time_msc = 0;
  if (m_curr_ticket)
    if (m_curr_deal.SelectByIndex(HistoryDealsTotal() - 1))
      pos_time_msc = m_curr_deal.TimeMsc();
  return (pos_time_msc);
}

ENUM_POSITION_TYPE CHistoryPositionInfo::PositionType(void) {
  ENUM_POSITION_TYPE pos_type = WRONG_VALUE;
  if (m_curr_ticket)
    if (m_curr_deal.SelectByIndex(0))
      pos_type = (ENUM_POSITION_TYPE)m_curr_deal.DealType();
  return (pos_type);
}

string CHistoryPositionInfo::TypeDescription(void) {
  string str;
  return (FormatType(str, PositionType()));
}

long CHistoryPositionInfo::Magic(void) {
  long pos_magic = WRONG_VALUE;
  if (m_curr_ticket)
    if (m_curr_deal.SelectByIndex(0))
      pos_magic = m_curr_deal.Magic();
  return (pos_magic);
}

long CHistoryPositionInfo::Identifier(void) {
  long pos_id = WRONG_VALUE;
  if (m_curr_ticket)
    if (m_curr_deal.SelectByIndex(0))
      pos_id = m_curr_deal.PositionId();
  return (pos_id);
}

ENUM_DEAL_REASON CHistoryPositionInfo::OpenReason(void) {
  ENUM_DEAL_REASON pos_reason = WRONG_VALUE;
  long reason;
  //--- if valid selection
  if (m_curr_ticket)
    if (m_curr_deal.SelectByIndex(0))
      if (m_curr_deal.InfoInteger(DEAL_REASON, reason))
        pos_reason = (ENUM_DEAL_REASON)reason;
  return (pos_reason);
}

ENUM_DEAL_REASON CHistoryPositionInfo::CloseReason(void) {
  ENUM_DEAL_REASON pos_reason = WRONG_VALUE;
  long reason;
  if (m_curr_ticket)
    if (m_curr_deal.SelectByIndex(HistoryDealsTotal() - 1))
      if (m_curr_deal.InfoInteger(DEAL_REASON, reason))
        pos_reason = (ENUM_DEAL_REASON)reason;
  return (pos_reason);
}

double CHistoryPositionInfo::Volume(void) {
  double pos_volume = WRONG_VALUE;
  if (m_curr_ticket)
    if (m_curr_deal.SelectByIndex(0))
      pos_volume = m_curr_deal.Volume();
  return (pos_volume);
}

double CHistoryPositionInfo::PriceOpen(void) {
  double pos_price = WRONG_VALUE;
  if (m_curr_ticket)
    if (m_curr_deal.SelectByIndex(0))
      pos_price = m_curr_deal.Price();
  return (pos_price);
}

double CHistoryPositionInfo::StopLoss(void) const {
  double pos_stoploss = WRONG_VALUE;
  long reason;
  CHistoryOrderInfo m_curr_order;
  if (m_curr_ticket)
    if (m_curr_order.SelectByIndex(HistoryOrdersTotal() - 1))
      if (m_curr_order.InfoInteger(ORDER_REASON, reason))
        if (reason == ORDER_REASON_SL)
          pos_stoploss = m_curr_order.PriceOpen();
        else if (m_curr_order.SelectByIndex(0))
          pos_stoploss = m_curr_order.StopLoss();
  return (pos_stoploss);
}

double CHistoryPositionInfo::TakeProfit(void) const {
  double pos_takeprofit = WRONG_VALUE;
  long reason;
  CHistoryOrderInfo m_curr_order;
  if (m_curr_ticket)
    if (m_curr_order.SelectByIndex(HistoryOrdersTotal() - 1))
      if (m_curr_order.InfoInteger(ORDER_REASON, reason))
        if (reason == ORDER_REASON_TP)
          pos_takeprofit = m_curr_order.PriceOpen();
        else if (m_curr_order.SelectByIndex(0))
          pos_takeprofit = m_curr_order.TakeProfit();
  return (pos_takeprofit);
}

double CHistoryPositionInfo::PriceClose(void) {
  double pos_cprice = WRONG_VALUE;
  double sumVolTemp = 0;
  double sumMulTemp = 0;

  if (m_curr_ticket)
    for (int i = 0; i < HistoryDealsTotal(); i++)
      if (m_curr_deal.SelectByIndex(i))
        if (m_curr_deal.Entry() == DEAL_ENTRY_OUT ||
            m_curr_deal.Entry() == DEAL_ENTRY_OUT_BY) {
          sumVolTemp += m_curr_deal.Volume();
          sumMulTemp += m_curr_deal.Price() * m_curr_deal.Volume();
          pos_cprice = sumMulTemp / sumVolTemp;
        }
  return (pos_cprice);
}

double CHistoryPositionInfo::Commission(void) {
  double pos_commission = 0;
  if (m_curr_ticket)
    for (int i = 0; i < HistoryDealsTotal(); i++)
      if (m_curr_deal.SelectByIndex(i))
        pos_commission += m_curr_deal.Commission();
  return (pos_commission);
}

double CHistoryPositionInfo::Swap(void) {
  double pos_swap = 0;
  if (m_curr_ticket)
    for (int i = 0; i < HistoryDealsTotal(); i++)
      if (m_curr_deal.SelectByIndex(i))
        pos_swap += m_curr_deal.Swap();
  return (pos_swap);
}

double CHistoryPositionInfo::Profit(void) {
  double pos_profit = 0;
  if (m_curr_ticket)
    for (int i = 0; i < HistoryDealsTotal(); i++)
      if (m_curr_deal.SelectByIndex(i))
        if (m_curr_deal.Entry() == DEAL_ENTRY_OUT ||
            m_curr_deal.Entry() == DEAL_ENTRY_OUT_BY)
          pos_profit += m_curr_deal.Profit();
  return (pos_profit);
}

string CHistoryPositionInfo::Symbol(void) {
  string pos_symbol = NULL;
  if (m_curr_ticket)
    if (m_curr_deal.SelectByIndex(0))
      pos_symbol = m_curr_deal.Symbol();
  return (pos_symbol);
}

string CHistoryPositionInfo::OpenComment(void) {
  string pos_comment = NULL;
  if (m_curr_ticket)
    if (m_curr_deal.SelectByIndex(0))
      pos_comment = m_curr_deal.Comment();
  return (pos_comment);
}

string CHistoryPositionInfo::CloseComment(void) {
  string pos_comment = NULL;
  //--- if valid selection
  if (m_curr_ticket)
    if (m_curr_deal.SelectByIndex(HistoryDealsTotal() - 1))
      pos_comment = m_curr_deal.Comment();
  return (pos_comment);
}

string CHistoryPositionInfo::OpenReasonDescription(void) {
  string str;
  return (FormatReason(str, OpenReason()));
}

string CHistoryPositionInfo::CloseReasonDescription(void) {
  string str;
  return (FormatReason(str, CloseReason()));
}

string CHistoryPositionInfo::DealTickets(const string separator = " ") {
  string str_deals = "";
  if (m_curr_ticket)
    for (int i = 0; i < HistoryDealsTotal(); i++)
      if (m_curr_deal.SelectByIndex(i)) {
        if (str_deals != "")
          str_deals += separator;
        str_deals += (string)m_curr_deal.Ticket();
      }
  return (str_deals);
}

string CHistoryPositionInfo::FormatType(string& str, const uint type) const {
  str = "";
  switch (type) {
    case POSITION_TYPE_BUY:
      str = "buy";
      break;
    case POSITION_TYPE_SELL:
      str = "sell";
      break;
    default:
      str = "unknown position type " + (string)type;
  }
  return (str);
}

string CHistoryPositionInfo::FormatReason(string& str,
                                          const uint reason) const {
  str = "";
  switch (reason) {
    case DEAL_REASON_CLIENT:
      str = "client";
      break;
    case DEAL_REASON_MOBILE:
      str = "mobile";
      break;
    case DEAL_REASON_WEB:
      str = "web";
      break;
    case DEAL_REASON_EXPERT:
      str = "expert";
      break;
    case DEAL_REASON_SL:
      str = "sl";
      break;
    case DEAL_REASON_TP:
      str = "tp";
      break;
    case DEAL_REASON_SO:
      str = "so";
      break;
    case DEAL_REASON_ROLLOVER:
      str = "rollover";
      break;
    case DEAL_REASON_VMARGIN:
      str = "vmargin";
      break;
    case DEAL_REASON_SPLIT:
      str = "split";
      break;
    default:
      str = "unknown reason " + (string)reason;
      break;
  }
  return (str);
}

bool CHistoryPositionInfo::HistorySelect(datetime from_date, datetime to_date) {
  if (!::HistorySelect(from_date, to_date)) {
    Print(__FUNCTION__ + " > Error: HistorySelect -> false. Error Code: ",
          GetLastError());
    return (false);
  }

  m_tickets.Shutdown();

  CHashSet<long> set_positions;
  long curr_pos_id;

  int deals = HistoryDealsTotal();
  for (int i = deals - 1; i >= 0 && !IsStopped(); i--)
    if (m_curr_deal.SelectByIndex(i))
      if (m_curr_deal.Entry() == DEAL_ENTRY_OUT ||
          m_curr_deal.Entry() == DEAL_ENTRY_OUT_BY)
        if (m_curr_deal.DealType() == DEAL_TYPE_BUY ||
            m_curr_deal.DealType() == DEAL_TYPE_SELL)
          if ((curr_pos_id = m_curr_deal.PositionId()) > 0)
            set_positions.Add(curr_pos_id);

  long arr_positions[];
  set_positions.CopyTo(arr_positions, 0);
  ArraySetAsSeries(arr_positions, true);

  int positions = ArraySize(arr_positions);
  for (int i = 0; i < positions && !IsStopped(); i++)
    if ((curr_pos_id = arr_positions[i]) > 0)
      if (HistoryPositionSelect(curr_pos_id))
        if (HistoryPositionCheck(0))
          if (!m_tickets.Add(curr_pos_id)) {
            Print(__FUNCTION__ + " > Error: failed to add position ticket #",
                  curr_pos_id);
            return (false);
          }
  return (true);
}

int CHistoryPositionInfo::PositionsTotal(void) const {
  return (m_tickets.Total());
}

bool CHistoryPositionInfo::SelectByTicket(const ulong ticket) {
  if (HistoryPositionSelect(ticket)) {
    if (HistoryPositionCheck(1)) {
      m_curr_ticket = ticket;
      return (true);
    }
  }
  m_curr_ticket = 0;
  return (false);
}

bool CHistoryPositionInfo::SelectByIndex(const int index) {
  ulong curr_pos_ticket = m_tickets.At(index);
  if (curr_pos_ticket < LONG_MAX) {
    if (HistoryPositionSelect(curr_pos_ticket)) {
      m_curr_ticket = curr_pos_ticket;
      return (true);
    }
  } else
    Print(__FUNCTION__ + " > Error: the index of selection is out of range.");

  m_curr_ticket = 0;
  return (false);
}

bool CHistoryPositionInfo::HistoryPositionSelect(const long position_id) const {
  if (!HistorySelectByPosition(position_id)) {
    Print(__FUNCTION__ +
              " > Error: HistorySelectByPosition -> false. Error Code: ",
          GetLastError());
    return (false);
  }
  return (true);
}

bool CHistoryPositionInfo::HistoryPositionCheck(const int log_level) {
  int deals = HistoryDealsTotal();
  if (deals < 2) {
    if (log_level > 0)
      Print(__FUNCTION__ + " > Error: the selected position is still open.");
    return (false);
  }
  double pos_open_volume = 0;
  double pos_close_volume = 0;
  for (int j = 0; j < deals; j++) {
    if (m_curr_deal.SelectByIndex(j)) {
      if (m_curr_deal.Entry() == DEAL_ENTRY_IN)
        pos_open_volume = m_curr_deal.Volume();
      else if (m_curr_deal.Entry() == DEAL_ENTRY_OUT ||
               m_curr_deal.Entry() == DEAL_ENTRY_OUT_BY)
        pos_close_volume += m_curr_deal.Volume();
    } else {
      Print(__FUNCTION__ + " > Error: failed to select deal at index #", j);
      return (false);
    }
  }

  if (MathAbs(pos_open_volume - pos_close_volume) > 0.00001) {
    if (log_level > 0)
      Print(__FUNCTION__ +
            " > Error: the selected position is not yet fully closed.");
    return (false);
  }

  return (true);
}
