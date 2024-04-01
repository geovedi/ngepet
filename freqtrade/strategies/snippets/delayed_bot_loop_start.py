# Preventing exchange overload from simultaneous bot requests.
# A proxy is not significantly effective in managing simultaneous requests 
# for the same currency pair from various bots.

import time
import numpy as np

class Evolver(IStrategy):

  def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        if self.dp.runmode.value in ('live', 'dry_run'):
            time.sleep(np.random.randint(0, 60))

