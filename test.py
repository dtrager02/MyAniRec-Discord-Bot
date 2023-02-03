import pandas as pd
data = [("a","b","c"),("d","e","f"),("g","h","j")]
df = pd.DataFrame(data,columns=["a","b","c"])
df[df['a'] == "d"].loc[:,'a'] = df[df['a'] == "d"].loc[:,'b']
df['ranks'] = pd.Series(range(len(df)))
print(str(df.loc[0,"ranks"]))

# print(type(df.loc[0,"a"]))