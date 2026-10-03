# EDA Findings

1. **Volume is growing steadily.** Average daily orders rose from 103 (first 90 days) to 150 (last 90 days), about **+46%**.
2. **Strong weekly rhythm.** Monday is the busiest day (174 orders) and Sunday the quietest (71).
3. **Primary bottleneck: Delhi Verification.** Average cycle time is 8.7h versus 5.2h for the same process at other centers, and 48% of its orders breach SLA.
4. **Quality degrades under load.** Error rate is 2.7% on the lightest-load days versus 5.5% on the heaviest quartile.
5. **Monday backlog.** Average cycle time is 8.3h on Mondays versus 7.0h on other days.

Overall: error rate 3.8%, SLA breach rate 12.2%.
