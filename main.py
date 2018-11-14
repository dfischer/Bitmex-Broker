#!/usr/bin/python

import bitmex
from subprocess import call
import time
import json

class StandingLimitOrder:
    #Standing limit order object
    def __init__(self, side, size, price):
        self.side = side
        self.size = size
        self.price = price

    def __str__(self):
        return """
        side: %s
        size: %s
        price: %s""" %(self.side, self.size, self.price)

class ActiveOrder:
    #Active order object
    def __init__(self, symbol, id, type, side, size, price, stopPx, timestamp):
        self.symbol = symbol
        self.id = id
        self.type = type
        self.side = side
        self.size = size
        self.price = price
        self.stopPx = stopPx
        self.timestamp = timestamp

    def __str__(self):
        return """|    %s    |    %s    |    %s    |    Size: %s    |    Price: %s    |    Stop Price: %s    |    %s    |""" %(self.symbol, self.type, self.side, self.size, self.price, self.stopPx, self.timestamp)

class Position:
    #Position object
    def __init__(self, symbol, entry, size, profit, timestamp):
        self.symbol = symbol
        self.entry = entry
        self.size = size
        self.profit = profit
        self.timestamp = timestamp

    def __str__(self):
        return """|    %s    |    Entry Price: %s    |    Size: %s    |    Profit(BTC): %s    |    %s    |""" %(self.symbol, self.entry, self.size, self.profit, self.timestamp)

class _Getch:
    """Gets a single character from standard input.  Does not echo to the
screen."""
    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except ImportError:
            self.impl = _GetchUnix()

    def __call__(self): return self.impl()

class _GetchUnix:
    def __init__(self):
        import tty, sys

    def __call__(self):
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

class _GetchWindows:
    def __init__(self):
        import msvcrt

    def __call__(self):
        import msvcrt
        return msvcrt.getch()

class BitmexWrapper:
    # Handles BitMex connection and interaction

    def __init__(self, test):
    # Establishes the connection to the api and loads the main menu
        if (test == 'y'):
            self.client = bitmex.bitmex(test=True, api_key='',api_secret='')

        else:
            self.client = bitmex.bitmex(test=False, api_key='',api_secret='')

        self.mainMenu()

    def getOrderBook(self, symbol, depth):
        #Fetches orderbook data from the API
        return self.client.OrderBook.OrderBook_getL2(symbol=symbol, depth=depth).result()

    def getActiveOrders(self, symbol):
        #Gets all the open orders on the specified symbol and puts it in a list of ActiveOrder objects
        orders = []

        aux = self.client.Order.Order_getOrders(symbol=symbol, filter='{"open":true}').result()

        for order in aux[0]:
            orders.append(ActiveOrder(order['symbol'], order['orderID'], order['ordType'], order['side'], order['orderQty'], order['price'], order['stopPx'], order['timestamp']))

        return orders

    def getAllActiveOrders(self):
        #Gets all active orders for every symbol and arranges them in a list of ActiveOrder objects

        orders = []

        aux = self.client.Order.Order_getOrders(filter='{"open":true}').result()

        for order in aux[0]:
            orders.append(ActiveOrder(order['symbol'], order['orderID'], order['ordType'], order['side'], order['orderQty'], order['price'], order['stopPx'], order['timestamp']))

        return orders

    def getOpenPosition(self, symbol):
        #Gets the current open position on the specified symbol and puts it in a list of Position objects
        aux = self.client.Position.Position_get(filter=json.dumps({"symbol": symbol})).result()

        #Conversion : satoshi -> BTC
        profit = aux[0][0]['unrealisedPnl'] * 0.00000001

        position = Position(aux[0][0]['symbol'], aux[0][0]['avgEntryPrice'], aux[0][0]['currentQty'], profit, aux[0][0]['timestamp'])

        return position

    def getAllPositions(self):
        #Gets all open positions and arranges them in a list of Position objects

        positions = []

        aux = self.client.Position.Position_get().result()

        for position in aux[0]:

            if (position['currentQty'] != 0):

                #Conversion: satoshi -> BTC
                profit = position['unrealisedPnl'] * 0.00000001

                positions.append(Position(position['symbol'], position['avgEntryPrice'], position['currentQty'], profit, position['timestamp']))

        return positions

    def getBestBidAsk(self, symbol, side):
        #Gets the best bid/ask price available in the order book for the specified side.
        orderBookJson = self.getOrderBook(symbol, 1)
        closestOrders = orderBookJson[0]

        for StandingLimitOrder in closestOrders :
            if (StandingLimitOrder['side'] == 'Sell'):
                bestAskPrice = StandingLimitOrder['price']

            elif (StandingLimitOrder['side'] == 'Buy'):
                bestBidPrice = StandingLimitOrder['price']

        if (side == 'Buy'):
            return bestBidPrice

        elif (side == 'Sell'):
            return bestAskPrice

    def calculateMakerOrderPrice(self, symbol, side):
        #Calculates the best possible price to place a limit order to be triggered as fast as possible without making a market order.
        #It uses the exchange smallest possible increment in price to calculate if the next incremented or decremented price is in between the spread.
        #If it is, it places the order at that price, if not, it places the order alongside the best bid/ask.
        buyPrice = self.getBestBidAsk(symbol,'Buy')
        sellPrice = self.getBestBidAsk(symbol,'Sell')

        if (side == 'Buy'):
            if (buyPrice + 0.5 >= sellPrice):
                orderPrice = buyPrice

            elif (buyPrice + 0.5 < sellPrice):
                orderPrice = buyPrice + 0.5

        elif (side == 'Sell'):
            if (sellPrice - 0.5 <= buyPrice):
                orderPrice = sellPrice

            elif (sellPrice - 0.5 > buyPrice):
                orderPrice = sellPrice - 0.5

        return orderPrice

    def getBalance(self):
    # Returns the user's account balance in BTC
        wallet = self.client.User.User_getMargin().result()
        satoshi = wallet[0]['walletBalance']
        balance = satoshi * 0.00000001
        return balance

    def getLeverage(self, symbol):
    # Returns the current leverage set for the specified symbol
        aux = self.client.Position.Position_get(filter=json.dumps({"symbol": symbol})).result()
        return aux[0][0]['leverage']

    def getCurrentPrice(self, symbol):
    #Gets the latest close price
        tradeBucket = self.client.Trade.Trade_getBucketed(binSize='1m', partial=True, symbol=symbol, reverse=True, count=1).result()
        price = tradeBucket[0][0]['close']
        return price

    def countAllOrders(self):
        #Counts all the active orders
        orders = self.getAllActiveOrders()
        return len(orders)

    def countAllPositions(self):
        #Counts all open Positions
        positions = self.getAllPositions()
        return len(positions)

    def printAccountInfo(self):
        #Prints the account's balance, number of active order and the number of open positions
        #To be used on all of the menus

        #IN THE FUTURE: It may also show how many orders were ordered to be closed and are currently waiting for it and trading stats such as profit, etc
        balance = self.getBalance()
        activeOrders = self.countAllOrders()
        openPositions = self.countAllPositions()

        print("ACCOUNT INFO\n\nBalance: ", balance)
        print("Total Active Orders: ", activeOrders)
        print("Total Open Positions: ", openPositions)

    def getPortfolioValue(self):
        #Sums the profit(in BTC) of all open Positions
        positions = self.getAllPositions()

        profit = 0

        for position in positions:
            profit = profit + position.profit

        return profit

    def drawMainMenu(self):

        call("clear")

        #Account Info Header + Main Menu
        print("############################################################################################################")
        self.printAccountInfo()
        print("############################################################################################################\n")
        print("1 - ENTRY MANAGEMENT\n2 - POSITION MANAGEMENT\n3 - PORTFOLIO OVERVIEW\nq - QUIT\n")
        print("############################################################################################################\n")

    def drawEntryManager(self, symbol, leverage):

        call("clear")
        print("############################################################################################################")
        self.printAccountInfo()
        print("############################################################################################################\n")
        print("ENTRY MANAGEMENT FOR: ", symbol)
        print("LEVERAGE: ", leverage)
        print("\n1 - LIMIT ENTRY\n2 - MARKET ENTRY\n3 - AGGRESSIVE LIMIT ENTRY\n4 - ORDER CANCELATION\n5 - SHOW ACTIVE ORDERS\n6 - SELECT ANOTHER INSTRUMENT\n7 - CHANGE LEVERAGE VALUE\nr - RETURN\nq - QUIT\n")
        print("############################################################################################################\n")

    def drawPositionManager(self, symbol):

        position = self.getOpenPosition(symbol)
        if (position.size == 0):
            message = 'There is currently no open position for this instrument'
        else:
            message = position

        call("clear")
        print("############################################################################################################")
        self.printAccountInfo()
        print("############################################################################################################\n")
        print("POSITION MANAGEMENT FOR: ", symbol)
        print(message)
        print("\n1 - LIMIT CLOSE\n2 - MARKET CLOSE\n3 - AGGRESSIVE LIMIT CLOSE\n4 - ADD/TAKE PROFIT\n5 - ORDER CANCELATION\n6 - SELECT ANOTHER INSTRUMENT\nr - RETURN\nq - QUIT\n")
        print("############################################################################################################\n")

    def drawPortfolioOverview(self):

        portfolio = self.getPortfolioValue()

        call("clear")
        print("############################################################################################################")
        self.printAccountInfo()
        print("############################################################################################################\n")
        print("PORTFOLIO OVERVIEW | Unrealised Portfolio PNL: ", portfolio)
        print("s - MARKET SELL PORTFOLIO r - RETURN\n")
        print("############################################################################################################\n")

    def drawLimitPlacer(self):

        call("clear")
        print("############################################################################################################")
        self.printAccountInfo()
        print("############################################################################################################\n")
        print("n - NEW LIMIT ENTRY\nr - RETURN\n")
        print("############################################################################################################\n")

    def drawMarketPlacer(self):

        call("clear")
        print("############################################################################################################")
        self.printAccountInfo()
        print("############################################################################################################\n")
        print("n - NEW MARKET ENTRY\nr - RETURN\n")
        print("############################################################################################################\n")

    def drawAggressivePlacer(self):

        call("clear")
        print("############################################################################################################")
        self.printAccountInfo()
        print("############################################################################################################\n")
        print("n - NEW AGGRESSIVE LIMIT ENTRY\nr - RETURN\n")
        print("############################################################################################################\n")

    def drawLimitCloser(self):

        call("clear")
        print("############################################################################################################")
        self.printAccountInfo()
        print("############################################################################################################\n")
        print("n - LIMIT CLOSE EXISTING POSITION ON THE SELECTED INSTRUMENT\nr - RETURN\n")
        print("############################################################################################################\n")

    def drawMarketCloser(self):

        call("clear")
        print("############################################################################################################")
        self.printAccountInfo()
        print("############################################################################################################\n")
        print("n - MARKET CLOSE EXISTING POSITION ON THE SELECTED INSTRUMENT\nr - RETURN\n")
        print("############################################################################################################\n")

    def drawAggressiveCloser(self):

        call("clear")
        print("############################################################################################################")
        self.printAccountInfo()
        print("############################################################################################################\n")
        print("n - AGRESSIVE CLOSE EXISTING POSITION ON THE SELECTED INSTRUMENT\nr - RETURN\n")
        print("############################################################################################################\n")

    def drawOrderKiller(self):

        call("clear")
        print("############################################################################################################")
        self.printAccountInfo()
        print("############################################################################################################\n")
        print("1 - CANCEL ORDER # (To be Implemented)\n2 - CANCEL ALL ORDERS\nr - RETURN\n")
        print("############################################################################################################\n")

    def drawOrderViewer(self):

        call("clear")
        print("############################################################################################################")
        self.printAccountInfo()
        print("############################################################################################################\n")
        print("ACTIVE ORDERS ON THE SELECTED INSTRUMENT. r - RETURN")
        print("############################################################################################################\n")

    def drawPositionViewer(self):

        call("clear")
        print("############################################################################################################")
        self.printAccountInfo()
        print("############################################################################################################\n")
        print("OPEN POSITION ON THE SELECTED INSTRUMENT. r - RETURN")
        print("############################################################################################################\n")

    def limitPlacer(self, symbol):
    #Asks the user to input the desired limit order price, the stop-loss and the risk. It then
    #calculates the size of the order based on the user input and the account's balance and places it
        try:

            balance = self.getBalance()
            limit = int(input("Limit Price:\n"))
            stop = int(input("Stop-Loss Price:\n"))
            riskInput = float(input("Risk %:\n"))
            risk = float(riskInput / 100)
            size = int((balance * risk) / ((limit - stop) / limit) * limit)

            self.client.Order.Order_new(symbol=symbol, orderQty = size, price = limit).result()
            self.client.Order.Order_new(symbol=symbol, orderQty = -(size), stopPx = stop).result()

        except KeyboardInterrupt:
            print("Keyboard Interrupt\n")

        except:
            print("CONNECTION ERROR. TRY AGAIN\n")

    def marketPlacer(self, symbol):
    #Asks the user to input the the stop-loss and the risk. It then checks if the order is a long or a short and sets the best bid/ask as
    #the entry price
    #then, it calculates the size of the order based on the user input, the entry price and the the account's balance and takes liquidity
        try:

            balance = self.getBalance()
            stop = int(input("Stop-Loss Price:\n"))
            riskInput = float(input("Risk %:\n"))
            risk = float(riskInput / 100)
            currentPrice = self.getCurrentPrice(symbol)

            if (stop > currentPrice):
                entry = self.getBestBidAsk(symbol, 'Buy')

            elif (stop < currentPrice):
                entry = self.getBestBidAsk(symbol, 'Sell')

            size = int((balance * risk) / ((entry - stop) / entry) * entry)

            if (size > entry):
                print("There is currently no sufficient liquidity depth to fill your order without slippage\n")
                time.sleep(1)
            else:
                self.client.Order.Order_new(symbol=symbol, orderQty = size, price = entry).result()
                self.client.Order.Order_new(symbol=symbol, orderQty = -(size), stopPx = stop).result()

        except KeyboardInterrupt:
            print("Keyboard Interrupt\n")

        except:
            print("CONNECTION ERROR. TRY AGAIN\n")

    def aggressivePlacer(self, symbol):
    #Asks the user to input the the stop-loss and the risk. It then checks if the order is a long or a short and sets most agressive price on desired side as
    #the entry price
    #then, it calculates the size of the order based on the user input, the entry price and the the account's balance and places a limit order so it can execute as soon as possible without taking liquidity
        try:

            balance = self.getBalance()
            stop = int(input("Stop-Loss Price:\n"))
            riskInput = float(input("Risk %:\n"))
            risk = float(riskInput / 100)
            currentPrice = self.getCurrentPrice(symbol)

            if (stop > currentPrice):
                entry = self.calculateMakerOrderPrice(symbol, 'Sell')

            elif (stop < currentPrice):
                entry = self.calculateMakerOrderPrice(symbol, 'Buy')

            size = int((balance * risk) / ((entry - stop) / entry) * entry)

            self.client.Order.Order_new(symbol=symbol, orderQty = size, price = entry).result()
            self.client.Order.Order_new(symbol=symbol, orderQty = -(size), stopPx = stop).result()


        except KeyboardInterrupt:
            print("Keyboard Interrupt\n")

        except:
            print("CONNECTION ERROR. TRY AGAIN\n")

    def limitCloser(self, symbol):
        # Gets the size of the current open position and uses it to place a limit order to close said position
        try:

            position = self.getOpenPosition(symbol)

            if (position.size == 0):
                print("There is currently no open position for this instrument.\n")
                time.sleep(1)
            else:
                limit = int(input("Limit Price:\n"))
                size = -(position.size)
                self.client.Order.Order_new(symbol=symbol, orderQty = size, price = limit).result()

        except KeyboardInterrupt:
            print("Keyboard Interrupt\n")

        except:
            print("CONNECTION ERROR. TRY AGAIN\n")

    def marketCloser(self, symbol):
        #Gets the size of the current open position and market closes it.
        try:

            position = self.getOpenPosition(symbol)

            if (position.size == 0):
                print("There is currently no open position for this instrument.\n")
                time.sleep(1)
            else:
                size = -(position.size)
                self.client.Order.Order_new(symbol=symbol, orderQty = size, ordType = 'Market').result()

                while (self.positionIsClosed(symbol) == False):
                    print ("Waiting for the position to be closed...\nPRESS CTRL+C TO QUIT THIS LOOP\n")

                self.cancelStop(symbol)


        except KeyboardInterrupt:
            print("Keyboard Interrupt\n")

        except:
            print("CONNECTION ERROR. TRY AGAIN\n")

    def aggressiveCloser(self, symbol):
        # Gets the current position's size on the specified symbol and places a limit order at the most aggressive price in order to close the correspoding position as soon as possible withou taking liquidity
        try:

            position = self.getOpenPosition(symbol)

            if (position.size == 0):
                print("There is currently no open position for this instrument.\n")
                time.sleep(1)

            else:
                size = -(position.size)

                if (size > 0):
                    entry = self.calculateMakerOrderPrice(symbol, 'Buy')

                elif (size < 0):
                    entry = self.calculateMakerOrderPrice(symbol, 'Sell')

                self.client.Order.Order_new(symbol=symbol, orderQty = size, price = entry).result()

                while (self.positionIsClosed(symbol) == False):
                    print ("Waiting for the position to be closed...\nPress CTRL+C TO QUIT THIS LOOP\n")

                self.cancelStop(symbol)

        except KeyboardInterrupt:
            print("Keyboard Interrupt\n")

        except:
            print("CONNECTION ERROR. TRY AGAIN\n")

    def positionIsClosed(self, symbol):
        #Cheks if the size of the current position on the specified symbol is 0. if it is, then the position is closed, otherwise, it is not
        position = self.getOpenPosition(symbol)

        if (position.size != 0):
            return False
        else:
            return True

    def cancelStop(self, symbol):
        #Loops through the active order list for the specified symbol and cancels the stop-loss
        #Note that the ADD/TAKE PROFIT section on Position Management is yet to be implemented so for now, the program is coded in a way that assumes that you will not use multiple orders on the same instrument
        orders = self.getActiveOrders(symbol)
        for order in orders:
            if (order.stopPx != None):
                self.cancelOrder(order.id)

    def cancelOrder(self, id):
        #Cancels the order with the provided id
        self.client.Order.Order_cancel(orderID = id).result()

    def cancelAllOrders(self, symbol):
    #For now it only cancels all the active order on the specified symbol
        try:
            self.client.Order.Order_cancelAll(symbol=symbol).result()

        except KeyboardInterrupt:
            print("Keyboard Interrupt\n")

        except:
            print("CONNECTION ERROR. TRY AGAIN\n")

    def sellPortfolio(self):
        #Iterates through all the positions and market closes them one by one
        sure = input("Are you sure?(y/n)\n")

        if (sure == 'y'):
            positions = self.getAllPositions()

            if (len(positions) == 0):
                print("There are currently no open positions you dumb fuck\n")
                time.sleep(1)
            else:
                for position in positions:
                    self.marketCloser(position.symbol)

        elif (sure =='n'):
            print("Ok.\n")
            time.sleep(1)

        else:
            self.invalidOption()

    def entryManagement(self):
        #ENTRY MANAGEMENT MENU

        #ALL TYPES OF ENTRIES NEEDS THE STOP-LOSS AND RISK% AS INPUT SO IT CAN CALCULATE THE SIZE OF THE ORDER BASED ON RISK AND PLACE IT

        #FUTURE: SMART STOP PLACING (SYNC STOP SIZE WITH ORDER FILLING OR PLACE THE STOP IF THE ORDER IS FILLED)
        call("clear")

        symbol = input("ENTER THE SYMBOL\n")
        leverage = self.getLeverage(symbol)

        getch = _Getch()

        while(True):

            self.drawEntryManager(symbol, leverage)

            userInput = getch.impl()

            if (userInput == '1'):

                self.drawLimitPlacer()

                userInput = getch.impl()

                if (userInput == 'n'):
                    self.limitPlacer(symbol)

                elif (userInput == 'r'):
                    continue

                else:
                    self.invalidOption()

            elif (userInput == '2'):

                self.drawMarketPlacer()

                userInput = getch.impl()

                if (userInput == 'n'):
                    self.marketPlacer(symbol)

                elif (userInput == 'r'):
                    continue

                else:
                    self.invalidOption()

            elif (userInput == '3'):

                self.drawAggressivePlacer()

                userInput = getch.impl()

                if (userInput == 'n'):
                    self.aggressivePlacer(symbol)

                elif (userInput == 'r'):
                    continue

                else:
                    self.invalidOption()

            elif (userInput == '4'):

                self.drawOrderKiller()

                userInput = getch.impl()

                if (userInput == '2'):
                    self.cancelAllOrders(symbol)

                elif (userInput == 'r'):
                    continue

                else:
                    self.invalidOption()

            elif (userInput == '5'):

                self.drawOrderViewer()

                orders = self.getActiveOrders(symbol)

                if (len(orders) == 0):
                    print("There are currently no active orders for this symbol\n")

                else:
                    [print(order) for order in orders]

                userInput = getch.impl()

                if (userInput == 'r'):
                    continue

                else:
                    self.invalidOption()

            elif (userInput == '6'):
                symbol = input("ENTER THE SYMBOL\n")
                leverage = self.getLeverage(symbol)

            elif (userInput == '7'):
                leverage = input("select your leverage (0-100)\n")
                self.client.Position.Position_updateLeverage(symbol=symbol, leverage=leverage).result()

            elif (userInput == 'r'):
                break

            elif (userInput == 'q'):
                self.quit()

            else:
                self.invalidOption()

    def positionManagement(self):
        #POSITION MANAGEMENT MENU
        #ALL TYPES OF ORDERS ARE USED TO CLOSE THE EXISTING POSITION ON THE SELECTED INSTRUMENT
        #EVERYTIME AN ORDER GETS CLOSED, THE CORRESPONDING STOP-LOSS IS CANCELED

        #TO DO IN THE FUTURE: EVERYTIME AND ORDER GETS CLOSED IT UPDATES THE STATS DATABASE (EXCEL MAYBE)
        call("clear")

        symbol = input("ENTER THE SYMBOL\n")

        getch = _Getch()

        while(True):

            self.drawPositionManager(symbol)

            userInput = getch.impl()

            if (userInput == '1'):

                self.drawLimitCloser()

                userInput = getch.impl()

                if (userInput == 'n'):
                    self.limitCloser(symbol)

                elif (userInput == 'r'):
                    continue
                else:
                    self.invalidOption()

            elif (userInput == '2'):

                self.drawMarketCloser()

                userInput = getch.impl()

                if(userInput == 'n'):
                    self.marketCloser(symbol)

                elif(userInput == 'r'):
                    continue

                else:
                    self.invalidOption()

            elif (userInput == '3'):

                self.drawAggressiveCloser()

                userInput = getch.impl()

                if(userInput == 'n'):
                    self.aggressiveCloser(symbol)

                elif(userInput == 'r'):
                    continue

                else:
                    self.invalidOption()

            elif (userInput == '5'):

                self.drawOrderKiller()

                userInput = getch.impl()

                if (userInput == '2'):
                    self.cancelAllOrders(symbol)

                elif (userInput == 'r'):
                    continue

                else:
                    self.invalidOption()

            elif (userInput == '6'):
                symbol = input("ENTER THE SYMBOL\n")

            elif (userInput == 'r'):
                break
            elif (userInput == 'q'):
                self.quit()
            else:
                self.invalidOption()

    def portfolioOverview(self):
        #Shows all open positions and their corresponding data
        self.drawPortfolioOverview()

        getch = _Getch()

        positions = self.getAllPositions()

        if (len(positions) == 0):
            print("There are currently no open positions\n")

        else:
            [print(position) for position in positions]

        userInput = getch.impl()

        if (userInput == 's'):
            self.sellPortfolio()

        elif (userInput == 'r'):
            self.mainMenu()

        else:
            self.invalidOption()

    def quit(self):
        print("Exiting the program...\n")
        time.sleep(1)
        exit()

    def invalidOption(self):
        print("Please enter a valid option.\n")
        time.sleep(1)

    def mainMenu(self):

        getch = _Getch()

        #BitMex Interaction session
        while(True):

            self.drawMainMenu()

            userInput = getch.impl()

            if (userInput == '1'):

                self.entryManagement()

            elif (userInput == '2'):

                self.positionManagement()

            elif (userInput == '3'):

                self.portfolioOverview()

            elif (userInput == 'q'):

                self.quit()

            else:

                self.invalidOption()

if __name__ == "__main__":
    #Asks the user if the program is to be run on testnet or not and creates an instance for BitmexWrapper
    while(True):
        call("clear")

        test = input("Run on testnet(y/n)?\n")


        if (test == 'y'):
            bot = BitmexWrapper('y')

        elif (test == 'n'):
            bot = BitmexWrapper('n')

        else:
            print ("Please enter a valid option.\n")
            time.sleep(1)
