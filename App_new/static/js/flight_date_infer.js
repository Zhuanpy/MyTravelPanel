/**
 * 航段日期年份推断（GDS 航段如 "13APR" 不带年份）
 *
 * 机票一般是今天或以后的日期，允许往前 30 天（出发后补录的情况）。
 * 取「不早于 今天-宽限天数」且「不早于 minDate（上一航段日期）」的最早那个日期的年份。
 * 例：今天 2026-10-05，13APR → 2027；28DEC 之后的 03JAN → 次年。
 *
 * 与后端 App_new/utils/parse_flights.py 的 infer_flight_year 保持一致。
 */
var FLIGHT_YEAR_GRACE_DAYS = 30;

function inferFlightYear(month, day, minDate) {
    var today = new Date();
    today.setHours(0, 0, 0, 0);
    var cutoff = new Date(today);
    cutoff.setDate(cutoff.getDate() - FLIGHT_YEAR_GRACE_DAYS);

    for (var year = today.getFullYear() - 1; year <= today.getFullYear() + 2; year++) {
        var candidate = new Date(year, month - 1, day);
        // 2月29日遇到非闰年会滚到3月1日，跳过
        if (candidate.getMonth() !== month - 1) continue;
        if (candidate < cutoff) continue;
        if (minDate && candidate < minDate) continue;
        return year;
    }
    return today.getFullYear();
}
