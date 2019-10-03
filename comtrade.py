"""Access UN Comtrade statistics from a python script.

Usage:
    df1 = country_export(reporter=276).dataframe('code') #all exports at HS 6-gigit level
    df2 = exporters(3102).dataframe() # Urea exports by country
    
Features:
   - requests_cache cache the calls, prevents overloading the API
   - 
    
Restrictions:
 - I looked with CommodityTrade trade, not services
 - year by default is 2018
 
Usage advice:
 - make a query at web interface, then check API for it    
 - exporter data may be more reliable that importer

API codumentation:
    https://comtrade.un.org/Data/doc/api/
    
"""    

from urllib.parse import urlencode, urlunsplit
from dataclasses import dataclass
import requests
import pandas as pd

import requests_cache

requests_cache.install_cache('comtrade_cache')

@dataclass
class Endpoint:
    query_string: str= ''
    scheme: str = 'http'
    netloc: str = 'comtrade.un.org'
    path: str = '/api/get'
    
    def url(self):
        return urlunsplit((self.scheme, 
                           self.netloc, 
                           self.path, 
                           self.query_string, 
                           ''))
        
        
from enum import Enum 
class Direction(Enum):
    Export = 2
    Import = 1


@dataclass
class CommodityTrade:
    code: int = 'AG6'
    year: int = 2018
    reporter: int = 'all'
    partner: int = 0    
    
    def set_reporter(self, reporter: int):
        self.reporter = reporter
        return self
    
    def raw_query(self, direction: Direction):
        return RawQuery(rg=direction.value, 
                        r=self.reporter, 
                        p=self.partner, 
                        cc=str(self.code), 
                        ps=self.year)

    def raw_query_export(self):
      return self.raw_query(Direction.Export)
           
    def raw_query_import(self):
      return self.raw_query(Direction.Export)    
    
    def get_export(self):
      return self.raw_query_export().response()

    def get_import(self):
      return self.raw_query_import().response()
  

@dataclass
class RawQuery:
    rg: int # 1 (imports) and 2 (exports)
    r: int # reporter
    p: int # partnter  
    cc: str = 'AG6'
    ps: int = 2018    
    freq: str = 'A'
    type: str = 'C' # C Commodities 
    px: str = 'HS'
    max: int = 50_000 
    
    @property
    def query_string(self):
        return urlencode(self.__dict__)
    
    @property
    def url(self):
        return Endpoint(query_string=self.query_string).url()   
    
    def get_json(self):
        return requests.get(self.url).json()        
    
    def response(self):
        return Response(self.get_json())
    
COL_DICT = dict(yr='year',
     rgDesc = 'dir',
     rtTitle='reporter',
     ptTitle='partner',
     cmdCode='code', 
     NetWeight='kg',
     TradeValue='usd',
     cmdDescE='desc')    


@dataclass
class Response:
    dict: dict   

    @property
    def dataset(self):
        return self.dict['dataset']
    
    @property
    def info(self):
        return self.dict['validation']
    
    def count(self):
        return self.info['count']['value']
    
    def dataframe(self, col_dict=COL_DICT, index_key=None):
        df = pd.DataFrame(self.dataset)[col_dict.keys()] \
                 .rename(columns=COL_DICT) \
                 .sort_values('usd', ascending=False)
        if index_key:
            df = df.set_index(index_key)
        df['musd'] = df.usd.divide(10**6).round(1)
        df['tton'] = df.kg.divide(10**6).round(1)
        df['price'] = (df.usd / df.kg).multiply(1000).round(1)    
        del df['usd']
        del df['kg']
        return df


def exporters(code, year=2018):
     return CommodityTrade(code, year).get_export().dataframe()   


def importers(code, year=2018):
     return CommodityTrade(code, year).get_import().dataframe()  

def estimate_price(df):
    df = df.query('tton > 0')
    df = df.groupby('code').sum()
    return (df.musd / df.tton).multiply(1000).round(1)
    
    
if __name__ == '__main__':
    
    # German exports to the world in 2018
    de = CommodityTrade(reporter=276).get_export()
    assert de.count() == de.dataframe().shape[0]

    # Firiliser exports by country
    amm = exporters(code=2814)
    nit = exporters(code=3102)
    pho = exporters(code=3103)
    pot = exporters(code=3104)
    mix = exporters(code=3105)
    
    df = pd.concat([amm, nit, pho, pot, mix])
    zf =  estimate_price(df)
    print (zf)
    
    for df in amm, nit, pho, pot, mix:
        code = df.code[0]
        print (code, df.desc[0])                
        del df['desc']
        del df['dir']
        del df['partner']
        del df['year']
        print(df.head(10))
        s = round(df.musd.sum() / 1000, 1)
        p = zf.loc[code,]
        t = round(s / p * 1000, 1)
        print("Totals:", t, s, p)
        
        
    wheat = exporters(100199).head(10)
    
    # /api/get?max=500&type=C&freq=A&px=HS&ps=2018&r=all&p=0&rg=all&cc=190531%2C190532
    #biscuit	190531, 190532
    
         
