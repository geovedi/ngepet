import fire
import re
from glob import glob
from string import Template

TEMPLATE = Template("""#include <fxsaber\\MultiTester\\MultiTester.mqh>

void SetTesterSettings()
{
    static const string ExpertNames[] = { 
        ${ea_list}
    };

    const int Size = ArraySize(ExpertNames);

    for (int i = 0; i < Size; i++)
        TesterSettings.Add(ExpertNames[i], "${symbol}", ${timeframe});
}
""")

def main(expert_dir, expert_name, symbol="Volatility 10 Index", tf="PERIOD_H1"):
    ea_list = [re.sub(r'\\', r'\\\\', e) for e in glob(f"{expert_dir}\\*.ex5")]
    ea_list = ["\"{0}\"".format(re.sub(r'^.*Experts\\\\', '', e)) for e in ea_list]
    ea_list = ',\n        '.join(ea_list)

    with open(f"{expert_name}", "w") as out:
        out.write(TEMPLATE.substitute(ea_list=ea_list, symbol=symbol, timeframe=tf))

if __name__ == '__main__':
    fire.Fire(main)
