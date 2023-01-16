from audioop import avg
import math
import ABR_data
from numpy import log
from utils import convertTo64x61


def calc_sum(data):
    sum = 0
    for element in data:
        sum += element
    return sum*1.0


def calc_premium(perp, spot):
    diff = []
    for i in range(len(perp)):
        diff.append((perp[i] - spot[i])/(perp[i] * 1.0))
    return diff


def calc_std(data, mean, boll_width):
    sum = 0
    length = len(data)
    for i in range(length):
        diff = data[i] - mean*1.0
        sum += diff**2.0

    if length > 1:
        length -= 1

    return boll_width*math.sqrt(sum/(length))


def find_jump(premium, perp, spot, lower, upper):
    for i in range(len(premium)):
        upper_diff = max(perp[i] - upper[i], 0)
        lower_diff = max(lower[i] - perp[i], 0)

        jump = 0
        if upper_diff > 0:
            jump = max(log(upper_diff)/spot[i], 0)
            premium[i] += jump

        if lower_diff > 0:
            jump = max(log(lower_diff)/spot[i], 0)
            premium[i] -= jump
    return premium


def sliding_mean(data, window):
    avg = []
    for i in range(len(data)):
        if i <= window - 1:
            avg.append(
                calc_sum(data[0:i + 1]) /
                (i+1)
            )
        else:
            avg.append(calc_sum(data[i-window + 1:i+1])/(window))
    return avg


def bollinger(data, avg, window, boll_width):
    lower = []
    upper = []

    for i in range(len(data)):
        if i <= window - 1:
            std = calc_std(data[0:i + 1], avg[i], boll_width)
            lower.append(avg[i] - std)
            upper.append(avg[i] + std)
        else:
            std = calc_std(data[i-window + 1:i+1], avg[i], boll_width)
            lower.append(avg[i] - std)
            upper.append(avg[i] + std)

    return (lower, upper)


def effective_abr(premium, base_rate):
    sum = 0
    for i in range(len(premium)):
        premium[i] /= 8.0
        premium[i] += base_rate
        sum += premium[i]
    return sum/len(premium)


def reduce(perp_spot, perp, window):
    index = []
    mark = []
    index_sum = 0
    mark_sum = 0
    for i in range(len(perp)):
        index_sum += perp_spot[i]
        mark_sum += perp[i]

        if (i+1) % window == 0:

            index.append(index_sum / window)
            mark.append(mark_sum / window)

            index_sum = 0
            mark_sum = 0
    return (index, mark)


def calculate_abr(perp_spot, perp, base_rate, boll_width):
    (index_prices, mark_prices) = reduce(
        perp_spot, perp, 8)
    avg_array = sliding_mean(mark_prices, 8)
    (lower, upper) = bollinger(mark_prices, avg_array, 8, boll_width)
    diff = calc_premium(mark_prices, index_prices)

    premium = sliding_mean(diff, 8)
    final_premium = find_jump(premium, mark_prices, index_prices, lower, upper)
    abr = effective_abr(final_premium, base_rate)
    return abr
