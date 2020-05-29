import logging
import re
import requests

from bs4 import BeautifulSoup
from lxml import etree


ENDPOINT = 'https://www.oilandgasnewsworldwide.com'
logging.basicConfig(format='[%(asctime)s] %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)


def get_url_error_handling(page_url):
    """
    The same as request but with error handling

    :param page_url: page url
    :return: response
    """
    try:
        return requests.get(page_url)
    except requests.exceptions.Timeout:
        logging.error('Maybe set up for a retry, or continue in a retry loop')
    except requests.exceptions.TooManyRedirects:
        logging.error('URL was bad and try a different one')
    except requests.exceptions.RequestException as e:
        logging.error('catastrophic error. bail.')
    raise SystemExit(e)


def get_companies_types_url():
    """
    Gathers data from the page:
    https://www.oilandgasnewsworldwide.com/OGNDirectory

    :return: list of company types urls
    """
    page = ENDPOINT + '/OGNDirectory'
    resp = get_url_error_handling(page)
    dom = etree.HTML(resp.text)
    pages_list = dom.xpath('//a[@class="fontLinkDirectory"]/@href')
    return pages_list


def get_companies_types_names():
    """
    Gathers data from the page:
    https://www.oilandgasnewsworldwide.com/OGNDirectory

    :return: list of company types names (without numbers)
    """
    page_url = ENDPOINT + '/OGNDirectory'
    resp = get_url_error_handling(page_url)
    dom = etree.HTML(resp.text)
    pages_list = dom.xpath('//a[@class="fontLinkDirectory"]')

    return [c_type.text.split(' (')[0] for c_type in pages_list]


def get_companies_data(company_type_url):
    """
    Gets companies data from the one page

    :param company_type_url: str rart of url to page
    :return: dict with metadata
    """
    companies = []
    page_url = ENDPOINT + company_type_url
    resp = get_url_error_handling(page_url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    soup_comp_meta = soup.find_all(attrs={"class": "fontsubsection nomarginpadding lmargin opensans"})

    for company in soup_comp_meta:
        meta = company.find_next_sibling().find_all('tr')

        all_metadata = []
        for m in meta:
            m_lst = m.find_all('td')

            m_data = []
            for ml in m_lst:
                str_text = _grooming(ml.text)
                m_data.append(str_text)
            all_metadata.append(m_data)

        company_data_dict = _parse_items(all_metadata)
        company_name = _grooming(company.text)
        company_data_dict['company_name'] = company_name

        logging.info(company_data_dict)

        companies.append(company_data_dict)

    return companies


def _grooming(any_string):
    """
    Removes whitespaces at the beginning at the end and \r \n

    :param any_string: raw string
    :return: pretty string
    """
    any_string = any_string.replace("\r", "")
    any_string = any_string.replace("\n", "")
    any_string = any_string.lstrip()
    any_string = any_string.rstrip()
    return any_string


def _parse_items(item_list):
    """
    Parse raw data from the page

    :param item_list: list of metadata
    :return: dict with metadata
    """
    out_dict = dict()
    phone_lst = []
    address_string = ''

    # Add some data to dictonary
    for item in item_list:
        for inst in ['Zip Code:', 'P.O Box:', 'City:', 'Country:']:
            if inst in item:
                item.remove(inst)
                out_dict[inst] = item[0]
                item.pop(0)

    for item in item_list:
        for inst in item:
            # check for phone numbers
            if len(re.sub("[^0-9]", "", inst)) > 8:
                phone_lst.append(inst.replace(" ", ""))
                item.remove(inst)

    # Phone and Address already added so they can be removed
    for item in item_list:
        for inst in item:
            if 'Phone:' in item or 'Address:' in item:
                item.remove(inst)

    # at this moment all additional data except address were removed
    for item in item_list:
        for inst in item:
            address_string = inst + address_string

    out_dict['Phone:'] = phone_lst
    address_string = _grooming(address_string)
    out_dict['Address:'] = address_string

    return out_dict


if __name__ == '__main__':
    company_type_url = '/Directory/AIPO/Air_Pollution_Control_'
    c_names = get_companies_data(company_type_url)
    # print(c_names)
