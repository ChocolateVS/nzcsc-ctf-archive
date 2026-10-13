from dataclasses import dataclass
import math
from pathlib import Path
import random


@dataclass
class Card():
    suit: str
    value: int

    def __str__(self):
        value = ['One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 'Jack', 'Queen', 'King'][self.value - 1]
        return f'{value} of {self.suit}'


DECK = [Card(suit, value) for value in range(1,14) for suit in ['Hearts', 'Diamonds', 'Spades', 'Clubs']]
NUM_DECKS_IN_SHOE = 2
SHOE = DECK * NUM_DECKS_IN_SHOE


class Hand():
    def __init__(self) -> None:
        self.cards: list[Card] = []

    @staticmethod
    def new():
        hand = Hand()
        hand.hit()
        hand.hit()
        return hand

    def hit(self):
        self.cards.append(SHOE.pop())
        return self.cards[-1]

    def value(self):
        total = 0
        for card in self.cards:
            total += card.value if card.value <= 10 else 10
        # account for aces (optionally add 10)
        if total <= 11 and any(x.value == 1 for x in self.cards):
            total += 10
        return total

    def is_blackjack(self):
        return self.value() == 21 and len(self.cards) == 2


WIN_AMOUNT = 1_000_000_000

def main():
    print('Welcome to the LuckyDay Casino')
    print('To get the flag you have to get to 1 billion dollars')

    balance = 1000

    print(f'Starting balance: ${balance}')

    while balance > 0 and balance < WIN_AMOUNT:
        print(f'Your balance is: {balance}')
        bet = int(input('Enter bet: '))
        if bet <= 0:
            raise Exception('nice try ... but the casio boss kicked you out')
        
        if bet > balance:
            print('Too much')
            return
        balance -= bet

        random.shuffle(SHOE)

        your_hand = Hand.new()
        dealer_hand = Hand.new()
        print(f'Dealer shows: {dealer_hand.cards[0]}')

        print('Your cards:')
        print(f' - {your_hand.cards[0]}')
        print(f' - {your_hand.cards[1]}')

        while len(your_hand.cards) < 5 and your_hand.value() <= 21:
            action = input(f'Your total is {your_hand.value()} - What do you want to do? (hit, stand, split) > ').lower()
            if action == 'hit':
                print(f'You drew: {your_hand.hit()}')
            elif action == 'stand':
                break
            elif action == 'split':
                if len(your_hand.cards) != 2:
                    raise Exception('Nice try - you cant split with more than two cards')
                your_hand.cards[1] = SHOE.pop()
                print('Your cards:')
                print(f' - {your_hand.cards[0]}')
                print(f' - {your_hand.cards[1]}')
                # TODO implement playing with the other split hand

        if your_hand.value() > 21:
            print('You went bust ... unlucky')
            result = 'lose'

        else:
            # Dealer hits on soft 17
            while dealer_hand.value() < 17 or (dealer_hand.value() == 17 and any(x.value == 1 for x in dealer_hand.cards)):
                dealer_hand.hit()
            print(f'Dealer cards: (total {dealer_hand.value()})')
            for card in dealer_hand.cards:
                print(f' - {card}')

            # Compare hands
            if dealer_hand.is_blackjack():
                if your_hand.is_blackjack():
                    result = 'tie'
                else:
                    result = 'lose'
            elif your_hand.is_blackjack():
                result = 'blackjack'
            elif dealer_hand.value() > 21:
                result = 'win'
            elif dealer_hand.value() < your_hand.value():
                result = 'win'
            elif dealer_hand.value() == your_hand.value():
                result = 'tie'
            else:
                result = 'lose'

        # Payday
        if result == 'blackjack':
            balance += math.floor(bet*2.5)
        elif result == 'win':
            balance += bet*2
        elif result == 'tie':
            balance += bet

        # Return cards to deck
        for card in your_hand.cards + dealer_hand.cards:
            SHOE.append(card)

        print(f'Result: {result}')


    if balance < WIN_AMOUNT:
        print('You lose')
        return

    print('What is your secret?')
    try:
        flag = Path('./flag.txt').read_text()
    except:
        flag = 'NZCSC{FAKE_FLAG_FOR_TESTING}'
    print(flag)


if __name__ == '__main__':
    main()
