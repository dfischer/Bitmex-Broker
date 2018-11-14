# Bitmex-Broker
CLI that lets the user manage his/her entries, positions and total portfolio on Bitmex exchange.  
Tested and developed using python 3.7.0

# Features
PLEASE NOTE: ALL ENTRY ORDERS ARE RISK ADJUSTED. THIS MEANS THAT WHEN THE USER WANTS TO SUBMIT A NEW ENTRY ORDER HE/SHE WILL BE ASKED TO INPUT THE DESIRED RISK PERCENTAGE TO BE TAKEN AND THE DESIRED STOP-LOSS PRICE IN ORDER TO GET A RISK-ADJUSTED POSITION SIZE. IN OTHER WORDS, THERE IS NO WAY TO SELECT THE SIZE OF THE ORDER, IT IS CALCULATED USING THE RISK, THE STOP-LOSS PRICE AND THE ENTRY-PRICE AND THERE IS NO OTHER WAY TO SUBMIT ENTRY ORDERS USING THIS PROGRAM.  
  
-> Risk-adjusted entry order submission.   
-> Aggressive orders (the order price is the closest possible price (+/- mininum bitmex increment) to the current price) - to be used as an alternative to market orders. This type of order is ideal when the user wants immediacy but is patient enough to not take liquidity.  
-> Stop-loss cancelation when the position is succefully closed (only available when the user tries to close the position with a market or an aggressive close order  
-> Portfolio overview (all existing positions and the total amount of unrealised profit in BTC)  
-> Portfolio selling (close all existing positions with market close orders)

# Requirements
Python 3.7.0  
Bravado and Bravado-core python libraries  

# Usage

Enter your api-key and secret (both for the testnet and the mainnet) on the __init__ function for the class BitmexWrapper located on main.py as the values for the api-key and api-secret arguments on the bitmex.bitmex function  
Run main.py with python3  
Choose between testnet or mainnet  
Enjoy. 

