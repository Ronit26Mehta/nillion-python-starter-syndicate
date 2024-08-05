from nada_dsl import *

def nada_main():
    company_a = Party(name="CompanyA")
    company_b = Party(name="CompanyB")
    auctioneer = Party(name="Auctioneer")
    bid_company_a = SecretInteger(Input(name="bid_company_a", party=company_a))
    bid_company_b = SecretInteger(Input(name="bid_company_b", party=company_b))
    is_bid_a_higher = bid_company_a < bid_company_b
    return [Output(is_bid_a_higher, name="is_bid_a_higher", party=auctioneer)]
