### 官方题解


### 个人题解

---

自己定义的状态：

- 第几天
- 是否持有股票
- 还剩几次卖出机会

转移方式：

- 买  or 不买
- 卖 or 不卖

注意去学习节约时间复杂度的做法

```cpp
class Solution {
public:
    int maxProfit(vector<int>& prices) {
        int n = prices.size();
        // day over, have, left_sell_cnt
        vector<vector<vector<int>>> dp(n + 1, vector<vector<int>>(2, vector<int>(3)));
        // int dp[n + 1][2][3];
        // dp[0][0][2] = 0;
        // dp[0][0][1] = 0;
        // dp[0][0][0] = 0;
        dp[0][1][2] = INT_MIN;
        dp[0][1][1] = INT_MIN;
        dp[0][1][0] = INT_MIN;
        
        for (int i = 1; i <= n; i++) {
            dp[i][0][2] = dp[i - 1][0][2];
            dp[i][0][1] = max(dp[i - 1][0][1], dp[i - 1][1][2] + prices[i - 1]);
            dp[i][0][0] = max(dp[i - 1][0][0], dp[i - 1][1][1] + prices[i - 1]);            

            dp[i][1][2] = max(dp[i - 1][1][2], dp[i - 1][0][2] - prices[i - 1]);
            dp[i][1][1] = max(dp[i - 1][1][1], dp[i - 1][0][1] - prices[i - 1]);
            dp[i][1][0] = max(dp[i - 1][1][1], dp[i - 1][0][0] - prices[i - 1]);
        }

        return max({dp[n][0][2],dp[n][0][1],dp[n][0][0]});
    }
};
```

---

https://leetcode.cn/problems/best-time-to-buy-and-sell-stock-iii/solutions/552695/mai-mai-gu-piao-de-zui-jia-shi-ji-iii-by-wrnt

因为转移只涉及到两天之间，所以可以先把个人题解中的三维数组变量都变成滚动数组的形式，再调换一下顺序，解决依赖问题，就可以不用滚动数组，直接用这几个变量：

```cpp
class Solution {
public:
    int maxProfit(vector<int>& prices) {
        int n = prices.size();
        int dp02 = 0;
        int dp01 = 0;
        int dp00 = 0;
        int dp12 = INT_MIN;
        int dp11 = INT_MIN;
        int dp10 = INT_MIN;
        
        for (int i = 1; i <= n; i++) {
            // dp02 = dp02;
            dp10 = max(dp11, dp00 - prices[i - 1]);
            dp00 = max(dp00, dp11 + prices[i - 1]);            
            dp11 = max(dp11, dp01 - prices[i - 1]);
            dp01 = max(dp01, dp12 + prices[i - 1]);
            dp12 = max(dp12, dp02 - prices[i - 1]);
        }

        return max({dp02, dp01, dp00});
    }
};
```
