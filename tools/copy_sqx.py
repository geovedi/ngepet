import os
import shutil
import hashlib
import fire
import pandas as pd

SHORT_WORDS = '''
act apt ask bad bag bat bed beg ben bet bid big bin bit bog bop bud bug
bum bun bus but cab cap cat cod cog con cop cot cud cup cut dab dad dan
den did dig dim dip dog don dot dug fad fan fat fed fig fin fit fog fun
gab gal gap gas gel gem get gig gin god got gum gun gus gut had ham has
hat hem hen hid him hip his hit hog hot hug hum hut jab jam jet jib jig
jog jot jug jut keg kid kin kit lab lad lag lap led leg let lid lip lit
lob log lop lot lug mad man map mat men met mob mom mop mug nap net nip
nod not nun nut odd pad pal pam pan peg pen pet pig pin pit pod pop pot
pug pun pup rag ram ran rat red rid rig rim rip rod rot rub rug rum run
rut sad sag sam sap sat set sin sip sit sod sub sum sun tab tad tag tan
tap ted ten tin tip tom top tot tug van vat vet wed wet win wit yam yet
zap zip
'''.strip().split()

def widx(x, n):
	return sum([ord(a) for i, a in enumerate(x) if i % n == 0])

def gwrd(i):
	return SHORT_WORDS[i % len(SHORT_WORDS)]

def hasher(s):
	x = hashlib.sha1(s).hexdigest()
	return '-'.join([gwrd(widx(x, i)) for i in range(2, 6)])

def main(portfolio, source_dir, target_dir, symbol_dir=True):
	df = pd.read_csv(portfolio)
	for _, porto in df.iterrows():
		porto_name = hasher(porto['Strategy Name'].encode())
		assets = porto['Symbol'].split(',')
		try:
			os.mkdir(f'{target_dir}\\{porto_name}')
		except:
			pass

		for asset in assets:
			if asset == 'Portfolio': continue
			if symbol_dir:
				symbol = asset.split('_')[0].strip()
				src_dir = f'{source_dir}\\{symbol}'
			else:
				src_dir = f'{source_dir}'
			print(porto_name, src_dir, asset)
			shutil.copy(f'{src_dir}\\{asset}.sqx', 
				        f'{target_dir}\\{porto_name}\\{asset}.sqx')


if __name__ == '__main__':
	fire.Fire(main)

