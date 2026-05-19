//+------------------------------------------------------------------+
//|                                         DailyTradeExporter.mq4   |
//|                              XM Affiliate SNS Auto Poster        |
//|                                                                  |
//| 【概要】                                                          |
//|   前日の取引履歴をCSVファイルとして出力するEAです。                   |
//|   出力されたCSVは、Pythonスクリプトによって読み込まれ、               |
//|   SaaSバックエンドAPIへ送信されます。                                |
//|                                                                  |
//| 【使い方】                                                        |
//|   1. このファイルをMT4の Experts フォルダにコピー                    |
//|   2. MT4でコンパイル                                               |
//|   3. 任意のチャートにアタッチ                                       |
//|   4. 毎日自動でCSVが出力されます                                    |
//+------------------------------------------------------------------+
#property copyright "XM Affiliate SNS Auto Poster"
#property link      ""
#property version   "1.00"
#property strict

// --- 入力パラメータ ---
input string CSVFileName = "daily_trade_data";  // CSVファイル名（拡張子なし）
input int    ExportHour  = 1;                    // CSV出力時刻（時、サーバー時間）

// --- グローバル変数 ---
datetime lastExportDate = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("DailyTradeExporter: 初期化完了");
    Print("CSV出力時刻: ", ExportHour, ":00 (サーバー時間)");
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                    |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("DailyTradeExporter: 終了");
}

//+------------------------------------------------------------------+
//| Expert tick function                                                |
//+------------------------------------------------------------------+
void OnTick()
{
    // 現在のサーバー時間を取得
    datetime currentTime = TimeCurrent();
    int currentHour = TimeHour(currentTime);
    datetime currentDate = StringToTime(TimeToString(currentTime, TIME_DATE));
    
    // 指定時刻かつ、当日まだ出力していない場合に実行
    if (currentHour >= ExportHour && lastExportDate < currentDate)
    {
        ExportDailyTrades(currentTime);
        lastExportDate = currentDate;
    }
}

//+------------------------------------------------------------------+
//| 前日の取引データをCSVに出力する関数                                   |
//+------------------------------------------------------------------+
void ExportDailyTrades(datetime currentTime)
{
    // 前日の日付範囲を計算
    datetime today = StringToTime(TimeToString(currentTime, TIME_DATE));
    datetime yesterday = today - 86400;  // 24時間前
    
    string dateStr = TimeToString(yesterday, TIME_DATE);
    
    Print("DailyTradeExporter: ", dateStr, " の取引データを出力中...");
    
    // 取引履歴の選択
    int totalOrders = OrdersHistoryTotal();
    
    double dailyProfit = 0;
    double dailyLoss = 0;
    int totalTrades = 0;
    int winningTrades = 0;
    int losingTrades = 0;
    
    for (int i = 0; i < totalOrders; i++)
    {
        if (OrderSelect(i, SELECT_BY_POS, MODE_HISTORY))
        {
            // 対象日のクローズ注文のみ集計
            datetime closeTime = OrderCloseTime();
            
            if (closeTime >= yesterday && closeTime < today)
            {
                // OP_BUY(0) または OP_SELL(1) のみ対象
                int orderType = OrderType();
                if (orderType == OP_BUY || orderType == OP_SELL)
                {
                    double profit = OrderProfit() + OrderSwap() + OrderCommission();
                    totalTrades++;
                    
                    if (profit >= 0)
                    {
                        dailyProfit += profit;
                        winningTrades++;
                    }
                    else
                    {
                        dailyLoss += profit;
                        losingTrades++;
                    }
                }
            }
        }
    }
    
    double netProfit = dailyProfit + dailyLoss;
    double winRate = 0;
    if (totalTrades > 0)
        winRate = NormalizeDouble((double)winningTrades / totalTrades * 100, 1);
    
    // アカウント情報
    double balance = AccountBalance();
    double equity = AccountEquity();
    string currency = AccountCurrency();
    
    // CSVファイルに出力
    string fileName = CSVFileName + "_" + 
                      StringReplace2(dateStr, ".", "-") + ".csv";
    
    int fileHandle = FileOpen(fileName, FILE_WRITE | FILE_CSV, ",");
    
    if (fileHandle != INVALID_HANDLE)
    {
        // ヘッダー行
        FileWrite(fileHandle, 
            "date", "platform", "account_balance", 
            "daily_profit", "daily_loss", "net_profit",
            "total_trades", "winning_trades", "losing_trades",
            "win_rate", "cumulative_profit", "currency");
        
        // データ行
        FileWrite(fileHandle,
            dateStr, "MT4", DoubleToString(balance, 2),
            DoubleToString(dailyProfit, 2), DoubleToString(dailyLoss, 2),
            DoubleToString(netProfit, 2),
            IntegerToString(totalTrades), IntegerToString(winningTrades),
            IntegerToString(losingTrades),
            DoubleToString(winRate, 1),
            DoubleToString(equity - balance, 2),
            currency);
        
        FileClose(fileHandle);
        
        Print("DailyTradeExporter: CSV出力完了 - ", fileName);
        Print("  損益: ", DoubleToString(netProfit, 2), " ", currency);
        Print("  勝率: ", DoubleToString(winRate, 1), "% (", 
              winningTrades, "勝", losingTrades, "敗)");
        Print("  取引回数: ", totalTrades);
    }
    else
    {
        Print("DailyTradeExporter: エラー - CSVファイルを開けません: ", fileName);
    }
}

//+------------------------------------------------------------------+
//| 文字列置換ヘルパー関数                                              |
//+------------------------------------------------------------------+
string StringReplace2(string str, string find, string replace)
{
    string result = str;
    StringReplace(result, find, replace);
    return result;
}
//+------------------------------------------------------------------+
