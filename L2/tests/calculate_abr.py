
import math
from numpy import log


perp_spot = [40915, 40945, 40945, 40956, 40943, 40944, 40960, 40948, 40934, 40942, 40955, 40944, 40918, 40927, 40907, 40901, 40917, 40937, 40964, 40959, 40957, 40914, 40914, 40911, 40897, 40909, 40911, 40924, 40942, 40947, 40951, 40941, 40926, 40937, 40962, 40971, 40984, 40956, 40956, 40953, 40941, 40930, 40923, 40923, 40923, 40892, 40905, 40927, 40894, 40899, 40890, 40896, 40900, 40917, 40904, 40933, 40933, 40962, 40967, 40998, 40989, 40980, 40971, 40959, 40975, 41005, 40953, 40974, 40949, 40968, 40949, 40946, 40942, 40925, 40908, 40908, 40900, 40925, 40948, 40931, 40927, 40942, 40937, 40951, 40954, 40950, 40940, 40931, 40926, 40915, 40939, 40929, 40940, 40925, 40947, 40948, 40913, 40915, 40904, 40907, 40887, 40879, 40877, 40879, 40881, 40877, 40884, 40920, 40921, 40927, 40926, 40943, 40916, 40903, 40903, 40942, 40942, 40937, 40980, 41007, 40993, 40986, 40929, 40887, 40895, 40891, 40915, 40850, 40847, 40843, 40843, 40823, 40826, 40847, 40842, 40844, 40849, 40854, 40851, 40833, 40812, 40816, 40829, 40804, 40811, 40791, 40767, 40768, 40768, 40767, 40767, 40758, 40748, 40735, 40732, 40740, 40745, 40709, 40711, 40712, 40761, 40754, 40744, 40738, 40741, 40737, 40729, 40692, 40692, 40685, 40677, 40682, 40683, 40696, 40724, 40687, 40697, 40727, 40696, 40701, 40701, 40699, 40706, 40711, 40747, 40737, 40742, 40742, 40766, 40733, 40714, 40723, 40712, 40709, 40701, 40704, 40715, 40685, 40665, 40656, 40658, 40677, 40688, 40695, 40700, 40707, 40703, 40699, 40695, 40686, 40708, 40650, 40730, 40735, 40744, 40741, 40691, 40692, 40691, 40690, 40692, 40712, 40740, 40734, 40701, 40738, 40686, 40734, 40788, 40787, 40781, 40784, 40790, 40793, 40800, 40801, 40818, 40824, 40837,
             40836, 40875, 40823, 40797, 40786, 40803, 40809, 40823, 40824, 40836, 40828, 40849, 40845, 40828, 40836, 40821, 40818, 40812, 40847, 40867, 40841, 40804, 40796, 40784, 40780, 40778, 40782, 40829, 40836, 40836, 40803, 40819, 40803, 40803, 40796, 40799, 40779, 40791, 40786, 40784, 40792, 40794, 40796, 40769, 40776, 40749, 40798, 40770, 40758, 40789, 40830, 40878, 40870, 40858, 40868, 40857, 40868, 40849, 40825, 40809, 40805, 40808, 40809, 40783, 40778, 40767, 40787, 40786, 40791, 40758, 40782, 40804, 40813, 40765, 40782, 40785, 40795, 40789, 40790, 40798, 40796, 40800, 40810, 40771, 40791, 40823, 40822, 40846, 40828, 40803, 40789, 40776, 40792, 40811, 40826, 40819, 40830, 40868, 40875, 40865, 40851, 40838, 40821, 40828, 40803, 40810, 40807, 40825, 40769, 40793, 40796, 40820, 40848, 40825, 40834, 40852, 40805, 40779, 40790, 40799, 40802, 40780, 40807, 40808, 40818, 40820, 40822, 40812, 40821, 40835, 40818, 40817, 40811, 40795, 40795, 40791, 40744, 40755, 40767, 40790, 40794, 40723, 40703, 40727, 40741, 40751, 40734, 40737, 40746, 40757, 40780, 40770, 40765, 40755, 40761, 40710, 40712, 40713, 40714, 40692, 40726, 40716, 40705, 40687, 40676, 40619, 40618, 40622, 40665, 40704, 40699, 40702, 40738, 40748, 40756, 40786, 40784, 40765, 40764, 40785, 40792, 40804, 40780, 40775, 40793, 40790, 40775, 40774, 40771, 40744, 40737, 40756, 40784, 40818, 40842, 40850, 40847, 40836, 40855, 40860, 40815, 40856, 40836, 40798, 40796, 40791, 40766, 40749, 40729, 40769, 40819, 40817, 40818, 40824, 40816, 40862, 40864, 40851, 40858, 40867, 40834, 40841, 40815, 40818, 40744, 40750, 40791, 40772, 40747, 40747, 40761, 40781, 40782, 40774, 40762, 40758, 40725, 40726, 40728, 40795, 40821]
perp = [40940, 40963, 40968, 40980, 40967, 40964, 40979, 40972, 40954, 40963, 40980, 40960, 40938, 40946, 40931, 40921, 40941, 40957, 40980, 40976, 40968, 40924, 40927, 40928, 40912, 40923, 40928, 40940, 40964, 40965, 40968, 40956, 40949, 40959, 40981, 40991, 40998, 40974, 40970, 40969, 40958, 40944, 40942, 40941, 40937, 40909, 40920, 40938, 40915, 40909, 40906, 40912, 40918, 40936, 40925, 40949, 40952, 40981, 40987, 41015, 41010, 41001, 40990, 40975, 40994, 41018, 40969, 40995, 40966, 40983, 40967, 40963, 40959, 40940, 40925, 40924, 40916, 40938, 40964, 40950, 40945, 40960, 40956, 40971, 40978, 40975, 40959, 40950, 40949, 40932, 40960, 40952, 40961, 40942, 40968, 40965, 40932, 40938, 40929, 40929, 40909, 40902, 40898, 40900, 40902, 40892, 40901, 40940, 40945, 40944, 40950, 40965, 40939, 40922, 40921, 40958, 40956, 40952, 40996, 41025, 41020, 41008, 40949, 40906, 40916, 40913, 40939, 40870, 40868, 40860, 40866, 40849, 40846, 40864, 40861, 40874, 40870, 40877, 40879, 40857, 40832, 40839, 40852, 40833, 40838, 40808, 40795, 40789, 40789, 40787, 40789, 40778, 40769, 40756, 40754, 40758, 40759, 40729, 40728, 40735, 40780, 40769, 40761, 40758, 40761, 40758, 40750, 40710, 40709, 40699, 40695, 40702, 40697, 40713, 40743, 40696, 40716, 40749, 40712, 40719, 40718, 40714, 40719, 40733, 40768, 40758, 40765, 40763, 40790, 40750, 40731, 40744, 40732, 40729, 40726, 40723, 40739, 40707, 40691, 40677, 40684, 40696, 40708, 40720, 40722, 40729, 40721, 40721, 40718, 40706, 40730, 40668, 40753, 40751, 40768, 40758, 40703, 40708, 40707, 40703, 40704, 40723, 40754, 40750, 40715, 40753, 40700, 40746, 40802, 40799, 40795, 40800, 40802, 40808, 40808, 40808, 40830, 40835, 40853, 40847,
        40888, 40838, 40812, 40798, 40817, 40822, 40840, 40843, 40855, 40844, 40857, 40859, 40842, 40850, 40833, 40830, 40825, 40860, 40880, 40859, 40823, 40812, 40802, 40797, 40791, 40796, 40845, 40852, 40850, 40821, 40835, 40823, 40823, 40819, 40819, 40794, 40805, 40806, 40802, 40807, 40812, 40811, 40789, 40795, 40768, 40814, 40788, 40774, 40806, 40851, 40900, 40891, 40892, 40897, 40886, 40888, 40864, 40844, 40828, 40827, 40827, 40825, 40802, 40798, 40788, 40809, 40804, 40808, 40778, 40803, 40831, 40835, 40787, 40799, 40803, 40815, 40811, 40809, 40815, 40816, 40818, 40832, 40792, 40812, 40844, 40846, 40865, 40852, 40831, 40812, 40801, 40817, 40837, 40851, 40842, 40851, 40890, 40892, 40886, 40873, 40860, 40844, 40856, 40828, 40835, 40832, 40851, 40798, 40820, 40821, 40846, 40871, 40851, 40860, 40884, 40826, 40800, 40811, 40823, 40826, 40802, 40830, 40826, 40840, 40842, 40848, 40833, 40841, 40860, 40848, 40841, 40833, 40813, 40821, 40816, 40763, 40775, 40792, 40815, 40818, 40744, 40724, 40746, 40762, 40771, 40749, 40758, 40766, 40774, 40802, 40791, 40785, 40774, 40779, 40732, 40735, 40735, 40741, 40712, 40748, 40737, 40728, 40712, 40704, 40637, 40642, 40657, 40685, 40730, 40729, 40728, 40765, 40772, 40784, 40814, 40811, 40794, 40793, 40811, 40817, 40826, 40804, 40798, 40819, 40817, 40802, 40801, 40798, 40772, 40761, 40778, 40811, 40843, 40868, 40878, 40879, 40863, 40884, 40885, 40846, 40885, 40866, 40827, 40822, 40823, 40795, 40777, 40760, 40799, 40850, 40842, 40853, 40853, 40845, 40891, 40896, 40880, 40888, 40894, 40867, 40874, 40848, 40842, 40774, 40778, 40822, 40798, 40777, 40772, 40785, 40809, 40809, 40804, 40787, 40790, 40753, 40753, 40751, 40819, 40845]


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


def calc_std(data, mean):
    sum = 0
    length = len(data)
    for i in range(length):
        diff = data[i] - mean
        sum += diff**2

    if length > 1:
        length -= 1

    return 2*math.sqrt(sum/(length))


def find_jump(premium, perp, spot, lower, upper):
    for i in range(len(premium)):
        upper_diff = max(perp[i] - upper[i], 0)
        lower_diff = max(lower[i] - perp[i], 0)

        if upper_diff > 0:
            jump = log(upper_diff/spot[i])
            premium[i] += jump

        if lower_diff > 0:
            jump = log(lower_diff/spot[i])
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


def bollinger(data, avg, window):
    lower = []
    upper = []

    for i in range(len(data)):
        if i <= window - 1:
            std = calc_std(data[0:i + 1], avg[i])
            lower.append(avg[i] - std)
            upper.append(avg[i] + std)
        else:
            std = calc_std(data[i-window + 1:i+1], avg[i])
            lower.append(avg[i] - std)
            upper.append(avg[i] + std)

    return (lower, upper)


def effective_abr(premium):
    sum = 0
    for i in range(len(premium)):
        premium[i] /= 8.0
        premium[i] += 0.0000125
        sum += premium[i]
    return sum/len(premium)


def main():
    avg_array = sliding_mean(perp[:100], 10)
    (lower, upper) = bollinger(perp[:100], avg_array, 10)

    diff = calc_premium(perp[:100], perp_spot[:100])
    premium = sliding_mean(diff, 60)
    # final_premium = find_jump(premium, perp, perp_spot, lower, upper)
    print(premium)
    # abr = effective_abr(final_premium)
    # print(abr)


main()

# #  @notice Function to calculate the sum of a given array
# # @param array_len - Length of the array
# # @param array - Array for which to calculate the sum
# # @param sum - Sum of the array
# # @returns sum - Final sum of the array
# func find_effective_ABR{syscall_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr}(
#     array_len : felt, array : felt*, sum : felt
# ) -> (sum : felt):
#     alloc_locals

#     # If reached the end of the array, return
#     if array_len == 0:
#         return (sum)
#     end

#     # Calculate the current sum
#     let (sum_temp) = Math64x61_div([array], 18446744073709551616)
#     let (sum_min) = Math64x61_add(sum_temp, 28823037615171)
#     let (curr_sum) = Math64x61_add(sum, sum_min)

#     # Recursively call the next array element
#     return find_effective_ABR(array_len - 1, array + 1, curr_sum)
# end
