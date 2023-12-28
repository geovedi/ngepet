import numpy as np
from pandas import DataFrame
from freqtrade.optimize.hyperopt import IHyperOptLoss

class SQNLoss(IHyperOptLoss):

    @staticmethod
    def hyperopt_loss_function(results: DataFrame, *args, **kwargs) -> float:
        profit = results['profit_abs']

        # Ensure chunks are of equal size for vectorization
        chunk_size = 100
        num_chunks = len(profit) // chunk_size
        truncated_profit = profit[:num_chunks * chunk_size]

        # Reshape and compute SQN for each chunk
        reshaped = truncated_profit.values.reshape(-1, chunk_size)
        mean = np.mean(reshaped, axis=1)
        std = np.std(reshaped, axis=1)

        # Avoid division by zero
        std[std == 0] = np.nan

        sqn_values = (mean / std) * np.sqrt(chunk_size)
        sqn_values = sqn_values[~np.isnan(sqn_values)]

        if len(sqn_values) == 0:
            return 0.0

        sqn = np.mean(sqn_values)
        return -sqn
