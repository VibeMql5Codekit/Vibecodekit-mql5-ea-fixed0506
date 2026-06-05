//+------------------------------------------------------------------+
//| CRiskGuard.mqh                                                    |
//|                                                                   |
//| Account-level safety net. Three independent rails:                |
//|   1) DailyLossLimit   — fraction of starting equity per day        |
//|   2) MaxOpenPositions — concurrent position cap                    |
//|   3) FreezeOnDD       — pause new entries when drawdown breached   |
//+------------------------------------------------------------------+
#ifndef __CRISK_GUARD_MQH__
#define __CRISK_GUARD_MQH__

class CRiskGuard
  {
private:
   double            m_daily_loss_limit_pct;
   int               m_max_open_positions;
   double            m_freeze_on_dd_pct;

   double            m_start_of_day_equity;
   datetime          m_day_anchor;
   bool              m_frozen;
   string            m_last_reason;

public:
                     CRiskGuard(void);
                    ~CRiskGuard(void) {}

   bool              Init(double daily_loss_pct,
                          int    max_positions,
                          double freeze_on_dd_pct);

   bool              CanOpenNewPosition(void);
   void              OnTick(void);
   string            LastBlockReason(void) const { return m_last_reason; }
   bool              IsFrozen(void)        const { return m_frozen; }
   double            DayStartEquity(void)  const { return m_start_of_day_equity; }

private:
   void              RollDayAnchor(void);
   int               CountOpenPositions(void);
  };

//+------------------------------------------------------------------+
CRiskGuard::CRiskGuard(void) : m_daily_loss_limit_pct(0.0),
                               m_max_open_positions(0),
                               m_freeze_on_dd_pct(0.0),
                               m_start_of_day_equity(0.0),
                               m_day_anchor(0),
                               m_frozen(false),
                               m_last_reason("")
  {
  }

//+------------------------------------------------------------------+
//| daily_loss_pct  : 0..1 (e.g. 0.05 = 5% per day cap)               |
//| max_positions   : 0 disables, else hard cap                       |
//| freeze_on_dd_pct: 0..1; freeze when equity ≤ start * (1 - pct)    |
//+------------------------------------------------------------------+
bool CRiskGuard::Init(double daily_loss_pct,
                      int    max_positions,
                      double freeze_on_dd_pct)
  {
   m_daily_loss_limit_pct = daily_loss_pct;
   m_max_open_positions   = max_positions;
   m_freeze_on_dd_pct     = freeze_on_dd_pct;
   m_start_of_day_equity  = AccountInfoDouble(ACCOUNT_EQUITY);
   m_day_anchor           = TimeCurrent();
   m_frozen               = false;
   m_last_reason          = "";
   return(true);
  }

//+------------------------------------------------------------------+
//| Roll the daily equity anchor at UTC midnight.                     |
//+------------------------------------------------------------------+
void CRiskGuard::RollDayAnchor(void)
  {
   datetime now = TimeCurrent();
   MqlDateTime now_struct, anchor_struct;
   TimeToStruct(now, now_struct);
   TimeToStruct(m_day_anchor, anchor_struct);
   if(now_struct.day != anchor_struct.day
      || now_struct.mon != anchor_struct.mon
      || now_struct.year != anchor_struct.year)
     {
      m_start_of_day_equity = AccountInfoDouble(ACCOUNT_EQUITY);
      m_day_anchor          = now;
      m_frozen              = false;
     }
  }

//+------------------------------------------------------------------+
//| Count positions across all symbols. Cheap enough for OnTick.      |
//+------------------------------------------------------------------+
int CRiskGuard::CountOpenPositions(void)
  {
   return(PositionsTotal());
  }

//+------------------------------------------------------------------+
//| Periodic recalc; call from OnTick (cheap) or OnTimer.             |
//+------------------------------------------------------------------+
void CRiskGuard::OnTick(void)
  {
   RollDayAnchor();
   if(m_freeze_on_dd_pct <= 0.0) return;
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(m_start_of_day_equity <= 0.0) return;
   double dd = (m_start_of_day_equity - eq) / m_start_of_day_equity;
   if(dd >= m_freeze_on_dd_pct) m_frozen = true;
  }

//+------------------------------------------------------------------+
//| Gate every entry on three rails: frozen, daily loss, max open.    |
//+------------------------------------------------------------------+
bool CRiskGuard::CanOpenNewPosition(void)
  {
   RollDayAnchor();
   if(m_frozen)
     {
      m_last_reason = "Frozen by drawdown";
      return(false);
     }
   if(m_daily_loss_limit_pct > 0.0 && m_start_of_day_equity > 0.0)
     {
      double eq = AccountInfoDouble(ACCOUNT_EQUITY);
      double loss = (m_start_of_day_equity - eq) / m_start_of_day_equity;
      if(loss >= m_daily_loss_limit_pct)
        {
         m_last_reason = "Daily loss limit breached";
         return(false);
        }
     }
   if(m_max_open_positions > 0 && CountOpenPositions() >= m_max_open_positions)
     {
      m_last_reason = "Max open positions reached";
      return(false);
     }
   m_last_reason = "";
   return(true);
  }

#endif // __CRISK_GUARD_MQH__
