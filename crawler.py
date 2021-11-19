import time
import platform
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.firefox.options import Options
from bs4.element import Tag
from bs4 import BeautifulSoup
from selenium import webdriver
from tabulate import tabulate
import json
import argparse


def get_soup(url):
    driver = webdriver.Firefox(executable_path='./geckodriver')
    driver.get(url)
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    return soup


def get_driver(url):
    os_type = platform.system()
    executable_path = './geckodriver'
    if os_type == 'Windows':
        executable_path += '.exe'
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Firefox(executable_path=executable_path, options=options)
    driver.get(url)
    return driver


def get_login_link():
    home_page_soup = get_soup('https://ctt.hust.edu.vn/')
    login_button_tag = home_page_soup.find('div', {'class': 'logIn'})
    login_link_tag = login_button_tag.find('a', {'id': 'loginLink'})
    login_link = login_link_tag.get_attribute_list('href')
    login_link = login_link[0]
    return login_link


def parse_course_general_info(course_tag: Tag):
    col_names = ['courseID', 'courseName', 'courseTime', 'numOfCredits', 'numOfFeeCredits', 'rate']
    course_general_info = dict()
    td_tags = course_tag.find_all('td', {'class': 'dxgv'})
    if not td_tags:
        return dict()
    td_tags.pop(0)
    count = 0
    for td_tag in td_tags:
        td_tag: Tag
        content = 'NULL'
        try:
            content = td_tag.contents[0]
        except Exception as e:
            print(e)
        course_general_info[col_names[count]] = content
        count += 1
    return course_general_info


def parse_course_detail_info(course_tag: Tag):
    col_names = ['preCourse', 'englishName', 'abbrName', 'institute']
    course_detail_info = dict()
    td_tag = course_tag.find('td', {'class': 'dxgv dxgvDetailCell_SisTheme'})
    b_tags = td_tag.find_all('b')
    count = 0
    for b_tag in b_tags:
        b_tag: Tag
        content = b_tag.contents
        if content:
            content = b_tag.contents[0]
        else:
            content = 'NULL'
        course_detail_info[col_names[count]] = content
        count += 1
    return course_detail_info


def get_course_info(course_id):
    course_list_page = get_driver('http://sis.hust.edu.vn/ModuleProgram/CourseLists.aspx')
    course_id_text_area = course_list_page.find_element_by_id('MainContent_tbCourseID_I')
    course_id_text_area.send_keys(course_id)
    course_id_text_area.send_keys(Keys.ENTER)
    time.sleep(1)
    table_element = course_list_page.find_element_by_id('MainContent_gvCoursesGrid_DXMainTable')
    try:
        # find the exactly course
        html = course_list_page.page_source
        soup = BeautifulSoup(html, "html.parser")
        table_tag = soup.find('table', {'id': 'MainContent_gvCoursesGrid'})
        all_data_row_tag = table_tag.find_all('tr', {'class': 'dxgvDataRow_SisTheme'})
        found_tag = Tag(name='null_tag')
        found_flag = False
        for row_tag in all_data_row_tag:
            general_info_course = parse_course_general_info(row_tag)
            crawled_course_id = general_info_course.get('courseID')
            if course_id.upper() == crawled_course_id:
                found_tag = row_tag
                found_flag = True
                break
        course_info = dict()

        if found_flag:
            # get general info of the course
            course_info.update(parse_course_general_info(found_tag))
            # find detail info of the course
            id_tag = found_tag.get_attribute_list('id')
            target_row = table_element.find_element_by_id(id_tag[0])
            expand_button = target_row.find_element_by_class_name('dxGridView_gvDetailCollapsedButton_SisTheme')
            expand_button.click()
            time.sleep(1)

            # get detail info of the course
            html = course_list_page.page_source
            soup = BeautifulSoup(html, "html.parser")
            table_tag = soup.find('table', {'id': 'MainContent_gvCoursesGrid'})
            detail_row_tag = table_tag.find('tr', {'class': 'dxgvDetailRow_SisTheme'})
            course_info.update(parse_course_detail_info(detail_row_tag))
        return course_info
    except NoSuchElementException as e:
        return None
    finally:
        course_list_page.close()


def console_ui():
    course_id = input('Nhập vào mã học phần: ')
    print('Đang lấy thông tin ...')
    course_info = get_course_info(course_id)
    if course_info:
        header = ['Mã học phần', 'Tên học phần', 'Thời lượng', 'Số tín chỉ', 'TC học phí', 'Trọng số',
                  'Học phần điều kiện', 'Tên tiếng anh', 'Tên viết tắt', 'Viện quản lý']
        data = []
        course_info_list = [course_info['courseID'], course_info['courseName'], course_info['courseTime'],
                            course_info['numOfCredits'], course_info['numOfFeeCredits'], course_info['rate'],
                            course_info['preCourse'], course_info['englishName'], course_info['abbrName'],
                            course_info['institute']
                            ]
        data.append(course_info_list)
        tbl = tabulate(data, headers=header)
        print(f'Thông tin học phần {course_id.upper()}: ')
        print(tbl)
    else:
        print('Không tìm thấy mã học phần vừa nhập!')


def write_file(file_name, course_id):
    course_info = get_course_info(course_id)
    with open(file_name, "w") as outfile:
        json.dump(course_info, outfile, indent=4, ensure_ascii=False)
    outfile.close()


def write_terminal(course_id):
    course_info = get_course_info(course_id)
    json_string = json.dumps(course_info, indent=4, ensure_ascii=False)
    print(json_string)


if __name__ == '__main__':
    # Initialize parser
    parser = argparse.ArgumentParser()

    # Adding optional argument
    parser.add_argument("-o", "--Output", help="Output file name")

    parser.add_argument("-s", "--Subject", help="Subject id")

    parser.add_argument("-t", "--Terminal", help="Show output on the terminal", required=False, action="store_true")
    # Read arguments from command line
    args = parser.parse_args()

    if args.Terminal:
        console_ui()
    elif args.Output and args.Subject:
        write_file(args.Output, args.Subject)
    elif args.Subject:
        write_terminal(args.Subject)
